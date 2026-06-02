import json
import boto3
import os
import hmac
import hashlib
import base64
import time
import uuid
import urllib.parse
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# ═══════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════
JWT_SECRET = os.environ.get('JWT_SECRET', 'cudeadaeve-k9mQ2xP7vL4nR8sT')

dynamodb = boto3.resource('dynamodb')

TABLE_MAPPING = {
    'habilidades': 'skills',
    'itens':       'itens',
    'personagens': 'characters',
    'escolas':     'schools',
    'categorias':  'categories',
    'lugares':     'places',
    'admins':      'admins',
    'treinamentos':'trainings',
    'mesas':       'mesas',
    'temporadas':  'temporadas',
    'musicas':     'musicas',
    'users':       'users',
    'invites':     'invites',
}

HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
}

# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

def resp(status, body):
    return {
        'statusCode': status,
        'headers': HEADERS,
        'body': json.dumps(body, cls=DecimalEncoder)
    }

def get_table(type_key):
    name = TABLE_MAPPING.get(type_key)
    if not name:
        raise ValueError(f"Tipo desconhecido: {type_key}")
    return dynamodb.Table(name)

def clean_item(obj):
    """Remove None e strings vazias — DynamoDB não aceita."""
    if isinstance(obj, dict):
        return {k: clean_item(v) for k, v in obj.items() if v is not None and v != ''}
    if isinstance(obj, list):
        return [clean_item(i) for i in obj]
    return obj

def parse_path(raw_path):
    """Retorna lista de segmentos, ignorando prefixo /prod ou /"""
    parts = [p for p in raw_path.split('/') if p and p != 'prod']
    return parts

# ═══════════════════════════════════════════════════════════
#  AUTH — JWT simples sem dependências externas
# ═══════════════════════════════════════════════════════════
def hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password, stored_hash):
    try:
        salt, _ = stored_hash.split(':', 1)
        return hash_password(password, salt) == stored_hash
    except Exception:
        return False

def generate_token(user_id, role):
    payload_str = json.dumps({
        'uid': user_id,
        'role': role,
        'exp': time.time() + 86400 * 7   # 7 dias
    })
    payload_b64 = base64.b64encode(payload_str.encode()).decode()
    sig = hmac.new(JWT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def validate_token(token_str):
    if not token_str:
        return None
    try:
        if token_str.startswith('Bearer '):
            token_str = token_str[7:]
        payload_b64, sig = token_str.rsplit('.', 1)
        expected = hmac.new(JWT_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(base64.b64decode(payload_b64).decode())
        if data.get('exp', 0) < time.time():
            return None
        return data
    except Exception:
        return None

def require_auth(event, roles=None):
    """Extrai JWT do header e retorna payload, ou None se inválido/ausente."""
    auth_header = (event.get('headers') or {}).get('Authorization', '')
    user = validate_token(auth_header)
    if not user:
        return None
    if roles and user.get('role') not in roles:
        return None
    return user

# ═══════════════════════════════════════════════════════════
#  ADMIN (sistema antigo — mantido para retrocompatibilidade)
# ═══════════════════════════════════════════════════════════
def validate_admin(admin_nome, admin_senha):
    if not admin_nome or not admin_senha:
        return None
    try:
        table = dynamodb.Table('admins')
        r = table.get_item(Key={'nome': admin_nome})
        admin = r.get('Item')
        if admin and admin.get('senha') == admin_senha:
            return admin
        return None
    except Exception as e:
        print(f"Erro ao validar admin: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#  ROUTE HANDLERS — AUTH
# ═══════════════════════════════════════════════════════════
def handle_login(body):
    nome  = (body.get('nome') or '').strip()
    senha = body.get('senha', '')
    if not nome or not senha:
        return resp(400, {'error': 'Nome e senha obrigatórios.'})

    try:
        table = dynamodb.Table('users')
        r = table.scan(FilterExpression=Attr('nome').eq(nome))
        items = r.get('Items', [])
        if not items:
            return resp(401, {'error': 'Usuário ou senha inválidos.'})

        user = items[0]
        if not verify_password(senha, user.get('senha_hash', '')):
            return resp(401, {'error': 'Usuário ou senha inválidos.'})

        token = generate_token(user['id'], user['role'])
        return resp(200, {
            'token': token,
            'user': {'id': user['id'], 'nome': user['nome'], 'role': user['role']}
        })
    except Exception as e:
        print(f"Login error: {e}")
        return resp(500, {'error': 'Erro interno no login.'})

def handle_register(body):
    """
    Criação de usuário via link de convite.
    Espera: { nome, senha, email, mesa_id, slot_id }
    """
    nome     = (body.get('nome') or '').strip()
    senha    = body.get('senha', '')
    email    = body.get('email', '')
    mesa_id  = body.get('mesa_id', '')
    slot_id  = body.get('slot_id', '')

    if not nome or not senha:
        return resp(400, {'error': 'Nome e senha obrigatórios.'})

    try:
        table = dynamodb.Table('users')

        # Checa se nome já existe
        existing = table.scan(FilterExpression=Attr('nome').eq(nome))
        if existing.get('Items'):
            return resp(409, {'error': 'Nome de usuário já em uso.'})

        new_user = {
            'id':         str(uuid.uuid4()),
            'nome':       nome,
            'email':      email,
            'senha_hash': hash_password(senha),
            'role':       'jogador'
        }
        table.put_item(Item=clean_item(new_user))

        # Se veio com convite de mesa, associa ao slot automaticamente
        if mesa_id and slot_id:
            _assign_player_to_slot(mesa_id, slot_id, new_user['id'], nome)

        token = generate_token(new_user['id'], 'jogador')
        return resp(200, {
            'token': token,
            'user':  {'id': new_user['id'], 'nome': nome, 'role': 'jogador'}
        })
    except Exception as e:
        print(f"Register error: {e}")
        return resp(500, {'error': 'Erro ao criar usuário.'})

# ═══════════════════════════════════════════════════════════
#  ROUTE HANDLERS — INVITE (SES)
# ═══════════════════════════════════════════════════════════
def handle_send_invite(body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})

    email    = (body.get('email') or '').strip()
    mesa_id  = body.get('mesa_id', '')
    slot_id  = body.get('slot_id', '')
    base_url = body.get('base_url', 'https://worldofeder.com.br/')

    if not email or not mesa_id or not slot_id:
        return resp(400, {'error': 'email, mesa_id e slot_id são obrigatórios.'})

    # Verifica se jogador já tem conta
    usuario_existente = None
    try:
        r = dynamodb.Table('users').scan(FilterExpression=Attr('email').eq(email))
        items = r.get('Items', [])
        if items:
            usuario_existente = items[0]
    except Exception:
        pass

    # Link varia conforme jogador tem conta ou não
    if usuario_existente:
        link = (f"{base_url}index.html"
                f"?mesa={urllib.parse.quote(mesa_id)}"
                f"&slot={urllib.parse.quote(slot_id)}")
    else:
        link = (f"{base_url}register.html"
                f"?mesa={urllib.parse.quote(mesa_id)}"
                f"&slot={urllib.parse.quote(slot_id)}"
                f"&email={urllib.parse.quote(email)}")

    # Busca nome da mesa e do mestre
    mesa_titulo = 'World Of Eder'
    mestre_nome = ''
    try:
        mesa = dynamodb.Table('mesas').get_item(Key={'id': mesa_id}).get('Item', {})
        mesa_titulo    = mesa.get('titulo', mesa_titulo)
        mestre_nome    = mesa.get('mestre_nome', '')
        mesa_msg_conv  = mesa.get('mensagem_convite', '')
    except Exception:
        mesa_msg_conv = ''

    from_email = os.environ.get('SES_FROM_EMAIL', 'no-reply@worldofeder.com')

    # Conteúdo dinâmico conforme jogador tem conta ou não
    if usuario_existente:
        nome_jogador  = usuario_existente.get('nome', 'Aventureiro')
        titulo_email  = 'Você foi Convocado!'
        subtitulo     = 'Sua presença é requerida'
        msg_principal = (f'O Mestre <strong style="color:#e6e0d4;">{mestre_nome}</strong> '
                         f'te convocou para a mesa')
        msg_secundaria = (mesa_msg_conv or
                          f'Você já possui uma conta, <strong style="color:#e6e0d4;">{nome_jogador}</strong>. '
                          f'Basta entrar no Hub para acessar sua ficha e se juntar à aventura.')
        cta_texto     = 'Acessar o Hub &rarr;'
        assunto       = f'Convocação para a mesa: {mesa_titulo} — World Of Eder'
    else:
        titulo_email  = 'Você foi Convidado!'
        subtitulo     = 'Um novo destino aguarda'
        msg_principal = (f'O Mestre <strong style="color:#e6e0d4;">{mestre_nome}</strong> '
                         f'te convidou para participar da mesa')
        msg_secundaria = (mesa_msg_conv or
                          'Crie sua conta para acessar a ficha do seu personagem, '
                          'explorar o mundo e entrar na aventura.')
        cta_texto     = 'Criar Minha Conta &rarr;'
        assunto       = f'Convite para a mesa: {mesa_titulo} — World Of Eder'

    html_body = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Convite — World Of Eder</title>
</head>
<body style="margin:0;padding:0;background-color:#08080f;font-family:Georgia,'Times New Roman',serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#08080f;padding:40px 16px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="560" cellpadding="0" cellspacing="0" border="0"
               style="max-width:560px;width:100%;background-color:#0d0d18;
                      border:1px solid #2a2316;border-radius:8px;overflow:hidden;">

          <!-- ── HEADER ── -->
          <tr>
            <td style="background-color:#0a0a12;padding:0;">
              <!-- Barra dourada superior -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td height="3" style="background:linear-gradient(90deg,transparent,#cfaa56,transparent);
                                        font-size:0;line-height:0;">&nbsp;</td>
                </tr>
              </table>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding:32px 32px 24px;">
                    <!-- Ornamento superior -->
                    <p style="margin:0 0 12px;color:#4a3f28;font-size:1.2rem;letter-spacing:8px;">
                      ✦ &nbsp; ✦ &nbsp; ✦
                    </p>
                    <!-- Título -->
                    <h1 style="margin:0;font-family:Georgia,serif;font-size:1.8rem;
                               font-weight:bold;letter-spacing:4px;color:#cfaa56;
                               text-transform:uppercase;">
                      World Of Eder
                    </h1>
                    <p style="margin:8px 0 0;font-size:0.7rem;color:#4a3f28;
                               letter-spacing:3px;text-transform:uppercase;">
                      Sistema de Fichas &amp; Mesas
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── DIVIDER ── -->
          <tr>
            <td style="padding:0 32px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td height="1" style="background-color:#1e1a10;font-size:0;line-height:0;">&nbsp;</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── BODY ── -->
          <tr>
            <td style="padding:36px 40px;">

              <!-- Ícone de convite -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding-bottom:24px;">
                    <table cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="background-color:#0f0f1a;border:1px solid #2a2316;
                                   border-radius:50%;width:64px;height:64px;
                                   text-align:center;vertical-align:middle;font-size:1.8rem;">
                          ⚔
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Título do convite -->
              <h2 style="margin:0 0 8px;font-family:Georgia,serif;font-size:1.25rem;
                         color:#cfaa56;text-align:center;letter-spacing:2px;">
                {titulo_email}
              </h2>
              <p style="margin:0 0 28px;font-size:0.78rem;color:#4a3f28;
                        text-align:center;letter-spacing:2px;text-transform:uppercase;">
                {subtitulo}
              </p>

              <!-- Mensagem principal -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#0a0a12;border:1px solid #1e1a10;
                            border-left:3px solid #cfaa56;border-radius:4px;margin-bottom:28px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 12px;color:#9a9488;font-size:0.9rem;line-height:1.8;">
                      {msg_principal}
                    </p>
                    <p style="margin:0;font-family:Georgia,serif;font-size:1.15rem;
                               color:#cfaa56;letter-spacing:1px;">
                      &#8220; {mesa_titulo} &#8221;
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 32px;color:#7a7468;font-size:0.85rem;
                        line-height:1.8;text-align:center;">
                {msg_secundaria}
              </p>

              <!-- Botão CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding-bottom:32px;">
                    <table cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td align="center"
                            style="background-color:#cfaa56;border-radius:4px;">
                          <a href="{link}"
                             style="display:inline-block;padding:14px 40px;
                                    font-family:Georgia,serif;font-size:0.9rem;
                                    font-weight:bold;letter-spacing:2px;
                                    color:#08080f;text-decoration:none;
                                    text-transform:uppercase;">
                            {cta_texto}
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Separador ornamental -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:24px;">
                <tr>
                  <td width="40%" height="1"
                      style="background-color:#1e1a10;font-size:0;line-height:0;">&nbsp;</td>
                  <td width="20%" align="center"
                      style="color:#4a3f28;font-size:0.75rem;padding:0 8px;">✦</td>
                  <td width="40%" height="1"
                      style="background-color:#1e1a10;font-size:0;line-height:0;">&nbsp;</td>
                </tr>
              </table>

              <!-- Link fallback -->
              <p style="margin:0 0 6px;color:#4a3f28;font-size:0.72rem;
                        text-align:center;letter-spacing:1px;text-transform:uppercase;">
                Se o botão não funcionar, acesse diretamente:
              </p>
              <p style="margin:0;text-align:center;">
                <a href="{link}"
                   style="color:#7a6a3a;font-size:0.72rem;word-break:break-all;
                          text-decoration:underline;">
                  {link}
                </a>
              </p>

            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="padding:0 32px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td height="1"
                      style="background-color:#1e1a10;font-size:0;line-height:0;">&nbsp;</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 40px;text-align:center;">
              <p style="margin:0 0 4px;color:#2a2316;font-size:0.68rem;letter-spacing:2px;">
                ✦ &nbsp; ✦ &nbsp; ✦
              </p>
              <p style="margin:0;color:#2a2316;font-size:0.68rem;letter-spacing:1px;">
                World Of Eder &mdash; Este convite é exclusivo para {email}
              </p>
            </td>
          </tr>

          <!-- Barra dourada inferior -->
          <tr>
            <td height="3"
                style="background:linear-gradient(90deg,transparent,#cfaa56,transparent);
                       font-size:0;line-height:0;">&nbsp;</td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>
  <!-- /Wrapper -->

</body>
</html>"""

    if usuario_existente:
        text_body = (f"Você foi convocado para a mesa '{mesa_titulo}' no World Of Eder.\n\n"
                     f"Você já possui uma conta. Acesse o Hub para entrar na aventura:\n{link}")
    else:
        text_body = (f"Você foi convidado para a mesa '{mesa_titulo}' no World Of Eder.\n\n"
                     f"Crie sua conta acessando o link abaixo:\n{link}")

    try:
        ses = boto3.client('ses', region_name='us-east-1')
        ses.send_email(
            Source=from_email,
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': assunto, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body,  'Charset': 'UTF-8'},
                    'Text': {'Data': text_body,  'Charset': 'UTF-8'},
                }
            }
        )
        # Salva registro do envio bem-sucedido
        try:
            dynamodb.Table('invites').put_item(Item={
                'id':               str(uuid.uuid4()),
                'email':            email,
                'mesa_id':          mesa_id,
                'mesa_titulo':      mesa_titulo,
                'slot_id':          slot_id,
                'mestre_id':        auth_user.get('uid', ''),
                'mestre_nome':      mestre_nome,
                'usuario_existente': bool(usuario_existente),
                'link':             link,
                'assunto':          assunto,
                'enviado_em':       time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'status':           'enviado'
            })
        except Exception as log_err:
            print(f"Erro ao salvar registro de invite: {log_err}")

        return resp(200, {'message': f'Convite enviado para {email}!', 'link': link})
    except Exception as e:
        print(f"SES error: {e}")
        # Retorna o link mesmo se o email falhou, para fallback no frontend
        return resp(500, {'error': str(e), 'link': link})

# ═══════════════════════════════════════════════════════════
#  ROUTE HANDLERS — USERS
# ═══════════════════════════════════════════════════════════
def handle_get_users(qs_params, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})

    search      = (qs_params or {}).get('search', '').lower()
    role_filter = (qs_params or {}).get('role', '')

    try:
        table = dynamodb.Table('users')
        r = table.scan()
        users = r.get('Items', [])

        if search:
            users = [u for u in users if search in u.get('nome', '').lower()
                                      or search in u.get('email', '').lower()]
        if role_filter:
            users = [u for u in users if u.get('role') == role_filter]

        return resp(200, [{'id': u['id'], 'nome': u['nome'], 'role': u.get('role')} for u in users])
    except Exception as e:
        print(f"Get users error: {e}")
        return resp(500, {'error': 'Erro ao buscar usuários.'})

# ═══════════════════════════════════════════════════════════
#  ROUTE HANDLERS — MESAS
# ═══════════════════════════════════════════════════════════
def handle_get_mesas(auth_user):
    if not auth_user:
        return resp(401, {'error': 'Autenticação necessária.'})

    try:
        table = dynamodb.Table('mesas')
        r = table.scan()
        mesas = r.get('Items', [])

        role = auth_user.get('role')
        uid  = auth_user.get('uid')

        if role == 'admin':
            pass
        elif role == 'mestre':
            mesas = [m for m in mesas if m.get('mestre_id') == uid]
        else:
            mesas = [m for m in mesas
                     if any(s.get('jogador_id') == uid for s in (m.get('slots') or []))]

        return resp(200, mesas)
    except Exception as e:
        print(f"Get mesas error: {e}")
        return resp(500, {'error': 'Erro ao buscar mesas.'})

def handle_create_mesa(body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Apenas mestres podem criar mesas.'})

    titulo = (body.get('titulo') or '').strip()
    if not titulo:
        return resp(400, {'error': 'Título obrigatório.'})

    # Admin pode especificar outro mestre; mestre sempre é o próprio usuário
    override = auth_user.get('role') == 'admin' and body.get('mestre_id')
    target_uid = body['mestre_id'] if override else auth_user['uid']

    mestre_nome = ''
    try:
        u = dynamodb.Table('users').get_item(Key={'id': target_uid}).get('Item')
        if u:
            mestre_nome = u.get('nome', '')
    except Exception:
        pass

    mesa = clean_item({
        'id':           str(uuid.uuid4()),
        'titulo':       titulo,
        'mestre_id':    target_uid,
        'mestre_nome':  mestre_nome,
        'archive_link': 'archive_from_eder.html',
        'slots':        []
    })

    try:
        dynamodb.Table('mesas').put_item(Item=mesa)
        return resp(200, mesa)
    except Exception as e:
        print(f"Create mesa error: {e}")
        return resp(500, {'error': 'Erro ao criar mesa.'})

def handle_update_mesa(mesa_id, body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    try:
        table = dynamodb.Table('mesas')
        mesa = table.get_item(Key={'id': mesa_id}).get('Item')
        if not mesa:
            return resp(404, {'error': 'Mesa não encontrada.'})
        if auth_user.get('role') != 'admin' and mesa.get('mestre_id') != auth_user['uid']:
            return resp(403, {'error': 'Você não é o mestre desta mesa.'})

        set_parts    = []
        expr_values  = {}
        remove_attrs = []

        if (body.get('titulo') or '').strip():
            set_parts.append('titulo = :titulo')
            expr_values[':titulo'] = body['titulo'].strip()

        if 'mensagem_convite' in body:
            msg = (body.get('mensagem_convite') or '').strip()
            if msg:
                set_parts.append('mensagem_convite = :msg_conv')
                expr_values[':msg_conv'] = msg
            else:
                remove_attrs.append('mensagem_convite')

        if 'mestre_id' in body and auth_user.get('role') == 'admin':
            mestre_id = body.get('mestre_id') or ''
            if mestre_id:
                u = dynamodb.Table('users').get_item(Key={'id': mestre_id}).get('Item') or {}
                set_parts.append('mestre_id = :mid')
                set_parts.append('mestre_nome = :mnome')
                expr_values[':mid']   = mestre_id
                expr_values[':mnome'] = u.get('nome', '')
            else:
                remove_attrs.extend(['mestre_id', 'mestre_nome'])

        if not set_parts and not remove_attrs:
            return resp(400, {'error': 'Nenhum campo para atualizar.'})

        update_expr = ''
        if set_parts:
            update_expr += 'SET ' + ', '.join(set_parts)
        if remove_attrs:
            update_expr += (' ' if update_expr else '') + 'REMOVE ' + ', '.join(remove_attrs)

        kwargs = {'Key': {'id': mesa_id}, 'UpdateExpression': update_expr.strip()}
        if expr_values:
            kwargs['ExpressionAttributeValues'] = expr_values

        table.update_item(**kwargs)
        return resp(200, {'message': 'Mesa atualizada.'})
    except Exception as e:
        print(f"Update mesa error: {e}")
        return resp(500, {'error': 'Erro ao atualizar mesa.'})

def handle_delete_mesa(mesa_id, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})

    try:
        table = dynamodb.Table('mesas')
        mesa = table.get_item(Key={'id': mesa_id}).get('Item')
        if not mesa:
            return resp(404, {'error': 'Mesa não encontrada.'})
        if auth_user.get('role') != 'admin' and mesa.get('mestre_id') != auth_user['uid']:
            return resp(403, {'error': 'Você não é o mestre desta mesa.'})

        table.delete_item(Key={'id': mesa_id})
        return resp(200, {'message': 'Mesa excluída.'})
    except Exception as e:
        print(f"Delete mesa error: {e}")
        return resp(500, {'error': 'Erro ao excluir mesa.'})

# ═══════════════════════════════════════════════════════════
#  ROUTE HANDLERS — SLOTS
# ═══════════════════════════════════════════════════════════
def _get_mesa_slots(mesa_id):
    table = dynamodb.Table('mesas')
    item = table.get_item(Key={'id': mesa_id}).get('Item')
    return table, item, list(item.get('slots', [])) if item else None

def _save_slots(table, mesa_id, slots):
    table.update_item(
        Key={'id': mesa_id},
        UpdateExpression='SET slots = :s',
        ExpressionAttributeValues={':s': clean_item(slots)}
    )

def handle_add_slot(mesa_id, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    try:
        table, mesa, slots = _get_mesa_slots(mesa_id)
        if mesa is None:
            return resp(404, {'error': 'Mesa não encontrada.'})
        new_slot = {
            'id': str(uuid.uuid4()),
            'jogador_id': None, 'jogador_nome': None,
            'personagem_id': None, 'personagem_nome': None,
            'ficha_liberada': False, 'experiencia': 0, 'nivel': 1
        }
        slots.append(new_slot)
        _save_slots(table, mesa_id, slots)
        return resp(200, new_slot)
    except Exception as e:
        print(f"Add slot error: {e}")
        return resp(500, {'error': 'Erro ao adicionar slot.'})

def handle_remove_slot(mesa_id, slot_id, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    try:
        table, mesa, slots = _get_mesa_slots(mesa_id)
        if mesa is None:
            return resp(404, {'error': 'Mesa não encontrada.'})
        slots = [s for s in slots if s.get('id') != slot_id]
        _save_slots(table, mesa_id, slots)
        return resp(200, {'message': 'Slot removido.'})
    except Exception as e:
        print(f"Remove slot error: {e}")
        return resp(500, {'error': 'Erro ao remover slot.'})

def handle_update_slot(mesa_id, slot_id, body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    try:
        table, mesa, slots = _get_mesa_slots(mesa_id)
        if mesa is None:
            return resp(404, {'error': 'Mesa não encontrada.'})
        for slot in slots:
            if slot.get('id') == slot_id:
                if 'experiencia' in body:
                    slot['experiencia'] = int(body['experiencia'])
                if 'nivel' in body:
                    slot['nivel'] = int(body['nivel'])
                break
        _save_slots(table, mesa_id, slots)
        return resp(200, {'message': 'Slot atualizado.'})
    except Exception as e:
        print(f"Update slot error: {e}")
        return resp(500, {'error': 'Erro ao atualizar slot.'})

def handle_toggle_ficha(mesa_id, slot_id, body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    liberada = bool(body.get('ficha_liberada', False))
    try:
        table, mesa, slots = _get_mesa_slots(mesa_id)
        if mesa is None:
            return resp(404, {'error': 'Mesa não encontrada.'})
        for slot in slots:
            if slot.get('id') == slot_id:
                slot['ficha_liberada'] = liberada
                break
        _save_slots(table, mesa_id, slots)
        return resp(200, {'message': f'Ficha {"liberada" if liberada else "bloqueada"}.'})
    except Exception as e:
        print(f"Toggle ficha error: {e}")
        return resp(500, {'error': 'Erro ao atualizar ficha.'})

def _assign_player_to_slot(mesa_id, slot_id, jogador_id, jogador_nome):
    table, mesa, slots = _get_mesa_slots(mesa_id)
    if not mesa:
        return
    for slot in slots:
        if slot.get('id') == slot_id:
            slot['jogador_id']   = jogador_id
            slot['jogador_nome'] = jogador_nome
            break
    _save_slots(table, mesa_id, slots)

def handle_assign_player(mesa_id, slot_id, body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    jogador_id = body.get('jogador_id')
    if not jogador_id:
        return resp(400, {'error': 'jogador_id obrigatório.'})
    try:
        u = dynamodb.Table('users').get_item(Key={'id': jogador_id}).get('Item') or {}
        jogador_nome = u.get('nome', '')
        _assign_player_to_slot(mesa_id, slot_id, jogador_id, jogador_nome)
        return resp(200, {'message': f'{jogador_nome} associado ao slot.'})
    except Exception as e:
        print(f"Assign player error: {e}")
        return resp(500, {'error': 'Erro ao associar jogador.'})

def handle_remove_player(mesa_id, slot_id, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    try:
        table, mesa, slots = _get_mesa_slots(mesa_id)
        if mesa is None:
            return resp(404, {'error': 'Mesa não encontrada.'})
        for slot in slots:
            if slot.get('id') == slot_id:
                slot.update({
                    'jogador_id': None, 'jogador_nome': None,
                    'personagem_id': None, 'personagem_nome': None,
                    'ficha_liberada': False
                })
                break
        _save_slots(table, mesa_id, slots)
        return resp(200, {'message': 'Jogador removido do slot.'})
    except Exception as e:
        print(f"Remove player error: {e}")
        return resp(500, {'error': 'Erro ao remover jogador.'})

def handle_add_item_to_player(mesa_id, slot_id, body, auth_user):
    if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
        return resp(403, {'error': 'Acesso negado.'})
    item_id = body.get('item_id')
    if not item_id:
        return resp(400, {'error': 'item_id obrigatório.'})
    try:
        _, mesa, slots = _get_mesa_slots(mesa_id)
        if not mesa:
            return resp(404, {'error': 'Mesa não encontrada.'})
        slot = next((s for s in slots if s.get('id') == slot_id), None)
        if not slot:
            return resp(404, {'error': 'Slot não encontrado.'})
        personagem_id = slot.get('personagem_id')
        if not personagem_id:
            return resp(400, {'error': 'Jogador ainda não tem personagem criado.'})

        chars_table = dynamodb.Table('characters')
        char = chars_table.get_item(Key={'id': personagem_id}).get('Item')
        if not char:
            return resp(404, {'error': 'Personagem não encontrado.'})

        itens_ids = list(char.get('itens_ids', []))
        if item_id not in itens_ids:
            itens_ids.append(item_id)
            chars_table.update_item(
                Key={'id': personagem_id},
                UpdateExpression='SET itens_ids = :i',
                ExpressionAttributeValues={':i': itens_ids}
            )
        return resp(200, {'message': 'Item adicionado ao inventário.'})
    except Exception as e:
        print(f"Add item error: {e}")
        return resp(500, {'error': 'Erro ao adicionar item.'})

# ═══════════════════════════════════════════════════════════
#  ROUTE HANDLERS — PERSONAGENS
# ═══════════════════════════════════════════════════════════
def handle_get_slot_personagem(mesa_id, slot_id, auth_user):
    """GET /mesas/{id}/slots/{sid}/personagem — carrega a ficha do slot."""
    try:
        mesas_table = dynamodb.Table('mesas')
        mesa = mesas_table.get_item(Key={'id': mesa_id}).get('Item')
        if not mesa:
            return resp(404, {'error': 'Mesa não encontrada.'})

        slot = next((s for s in (mesa.get('slots') or []) if s.get('id') == slot_id), None)
        if not slot:
            return resp(404, {'error': 'Slot não encontrado.'})

        # Verifica acesso: o próprio jogador, o mestre da mesa ou admin
        uid  = (auth_user or {}).get('uid', '')
        role = (auth_user or {}).get('role', '')
        is_owner  = slot.get('jogador_id') == uid
        is_mestre = mesa.get('mestre_id') == uid
        if role != 'admin' and not is_owner and not is_mestre:
            return resp(403, {'error': 'Acesso negado.'})

        personagem_id = slot.get('personagem_id')
        personagem    = None

        if personagem_id:
            char_item = dynamodb.Table('characters').get_item(Key={'id': personagem_id}).get('Item')
            personagem = char_item

        return resp(200, {
            'personagem':     personagem,
            'slot':           slot,
            'mesa':           {'id': mesa['id'], 'titulo': mesa.get('titulo', ''),
                               'mestre_nome': mesa.get('mestre_nome', '')},
            'ficha_liberada': bool(slot.get('ficha_liberada', False)),
        })
    except Exception as e:
        print(f"Get slot personagem error: {e}")
        return resp(500, {'error': 'Erro ao carregar ficha.'})


def handle_create_slot_personagem(mesa_id, slot_id, body, auth_user):
    """POST /mesas/{id}/slots/{sid}/personagem — cria ficha para o slot."""
    if not auth_user:
        return resp(401, {'error': 'Autenticação necessária.'})

    try:
        mesas_table = dynamodb.Table('mesas')
        mesa = mesas_table.get_item(Key={'id': mesa_id}).get('Item')
        if not mesa:
            return resp(404, {'error': 'Mesa não encontrada.'})

        slots = mesa.get('slots') or []
        slot  = next((s for s in slots if s.get('id') == slot_id), None)
        if not slot:
            return resp(404, {'error': 'Slot não encontrado.'})

        uid  = auth_user.get('uid', '')
        role = auth_user.get('role', '')
        is_owner  = slot.get('jogador_id') == uid
        is_mestre = mesa.get('mestre_id') == uid
        if role != 'admin' and not is_owner and not is_mestre:
            return resp(403, {'error': 'Acesso negado.'})

        # Cria o personagem
        personagem_id = str(uuid.uuid4())
        personagem    = clean_item({
            **body,
            'id':       personagem_id,
            'mesa_id':  mesa_id,
            'slot_id':  slot_id,
            'jogador_id': slot.get('jogador_id', uid),
        })
        dynamodb.Table('characters').put_item(Item=personagem)

        # Atualiza slot com personagem_id e nome
        for s in slots:
            if s.get('id') == slot_id:
                s['personagem_id']   = personagem_id
                s['personagem_nome'] = body.get('nome', '')
                break
        _save_slots(mesas_table, mesa_id, slots)

        return resp(200, personagem)
    except Exception as e:
        print(f"Create personagem error: {e}")
        return resp(500, {'error': 'Erro ao criar ficha.'})


def handle_update_personagem(personagem_id, body, auth_user):
    """PUT /personagens/{id} — atualiza ficha via JWT."""
    if not auth_user:
        return resp(401, {'error': 'Autenticação necessária.'})

    try:
        chars_table = dynamodb.Table('characters')
        existing    = chars_table.get_item(Key={'id': personagem_id}).get('Item')
        if not existing:
            return resp(404, {'error': 'Personagem não encontrado.'})

        uid  = auth_user.get('uid', '')
        role = auth_user.get('role', '')
        # Permissão: dono da ficha, mestre da mesa ou admin
        is_owner = existing.get('jogador_id') == uid
        if not is_owner and role not in ('mestre', 'admin'):
            return resp(403, {'error': 'Acesso negado.'})

        # Se mestre/admin, confirma que é mestre da mesa correta
        if not is_owner and role == 'mestre':
            mesa = dynamodb.Table('mesas').get_item(
                Key={'id': existing.get('mesa_id', '')}
            ).get('Item', {})
            if mesa.get('mestre_id') != uid:
                return resp(403, {'error': 'Você não é o mestre desta mesa.'})

        updated = clean_item({
            **existing,
            **body,
            'id':       personagem_id,
            'mesa_id':  existing.get('mesa_id'),
            'slot_id':  existing.get('slot_id'),
            'jogador_id': existing.get('jogador_id'),
        })
        chars_table.put_item(Item=updated)

        # Atualiza nome no slot se mudou
        if body.get('nome') and existing.get('mesa_id') and existing.get('slot_id'):
            try:
                mesas_table = dynamodb.Table('mesas')
                mesa        = mesas_table.get_item(Key={'id': existing['mesa_id']}).get('Item')
                if mesa:
                    slots = mesa.get('slots') or []
                    for s in slots:
                        if s.get('id') == existing['slot_id']:
                            s['personagem_nome'] = body['nome']
                            break
                    _save_slots(mesas_table, existing['mesa_id'], slots)
            except Exception:
                pass

        return resp(200, {'message': 'Ficha salva com sucesso!'})
    except Exception as e:
        print(f"Update personagem error: {e}")
        return resp(500, {'error': 'Erro ao salvar ficha.'})

# ═══════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════
def route_new_api(http_method, parts, body, qs, auth_user):
    """
    Roteia as novas rotas do Lobby.
    parts = segmentos do path sem /prod, ex: ['mesas', 'm1', 'slots', 's1', 'unlock']
    """
    # POST /auth/login
    if parts == ['auth', 'login'] and http_method == 'POST':
        return handle_login(body)

    # POST /auth/register
    if parts == ['auth', 'register'] and http_method == 'POST':
        return handle_register(body)

    # POST /auth/invite
    if parts == ['auth', 'invite'] and http_method == 'POST':
        return handle_send_invite(body, auth_user)

    # GET /invites  — histórico de convites (mestre/admin)
    if parts == ['invites'] and http_method == 'GET':
        if not auth_user or auth_user.get('role') not in ('mestre', 'admin'):
            return resp(403, {'error': 'Acesso negado.'})
        try:
            table = dynamodb.Table('invites')
            r     = table.scan()
            items = r.get('Items', [])
            # Filtra por mestre se não for admin
            if auth_user.get('role') == 'mestre':
                items = [i for i in items if i.get('mestre_id') == auth_user.get('uid')]
            # Filtra por mesa se passado como query param
            mesa_filter = qs.get('mesa_id')
            if mesa_filter:
                items = [i for i in items if i.get('mesa_id') == mesa_filter]
            # Ordena do mais recente para o mais antigo
            items.sort(key=lambda x: x.get('enviado_em', ''), reverse=True)
            return resp(200, items)
        except Exception as e:
            print(f"Get invites error: {e}")
            return resp(500, {'error': 'Erro ao buscar histórico de convites.'})

    # GET /users
    if parts == ['users'] and http_method == 'GET':
        return handle_get_users(qs, auth_user)

    # /mesas
    if not parts or parts[0] != 'mesas':
        return None

    # GET /mesas
    if len(parts) == 1 and http_method == 'GET':
        return handle_get_mesas(auth_user)

    # POST /mesas
    if len(parts) == 1 and http_method == 'POST':
        return handle_create_mesa(body, auth_user)

    if len(parts) < 2:
        return None
    mesa_id = parts[1]

    # PUT /mesas/{id}
    if len(parts) == 2 and http_method == 'PUT':
        return handle_update_mesa(mesa_id, body, auth_user)

    # DELETE /mesas/{id}
    if len(parts) == 2 and http_method == 'DELETE':
        return handle_delete_mesa(mesa_id, auth_user)

    if len(parts) < 3 or parts[2] != 'slots':
        return None

    # POST /mesas/{id}/slots
    if len(parts) == 3 and http_method == 'POST':
        return handle_add_slot(mesa_id, auth_user)

    if len(parts) < 4:
        return None
    slot_id = parts[3]

    # PUT /mesas/{id}/slots/{sid}  — xp / nivel
    if len(parts) == 4 and http_method == 'PUT':
        return handle_update_slot(mesa_id, slot_id, body, auth_user)

    # DELETE /mesas/{id}/slots/{sid}
    if len(parts) == 4 and http_method == 'DELETE':
        return handle_remove_slot(mesa_id, slot_id, auth_user)

    if len(parts) < 5:
        return None
    action = parts[4]

    # PUT /mesas/{id}/slots/{sid}/unlock
    if action == 'unlock' and http_method == 'PUT':
        return handle_toggle_ficha(mesa_id, slot_id, body, auth_user)

    # PUT /mesas/{id}/slots/{sid}/assign
    if action == 'assign' and http_method == 'PUT':
        return handle_assign_player(mesa_id, slot_id, body, auth_user)

    # DELETE /mesas/{id}/slots/{sid}/assign
    if action == 'assign' and http_method == 'DELETE':
        return handle_remove_player(mesa_id, slot_id, auth_user)

    # POST /mesas/{id}/slots/{sid}/items
    if action == 'items' and http_method == 'POST':
        return handle_add_item_to_player(mesa_id, slot_id, body, auth_user)

    # GET|POST /mesas/{id}/slots/{sid}/personagem
    if action == 'personagem':
        if http_method == 'GET':
            return handle_get_slot_personagem(mesa_id, slot_id, auth_user)
        if http_method == 'POST':
            return handle_create_slot_personagem(mesa_id, slot_id, body, auth_user)

    return None

# ═══════════════════════════════════════════════════════════
#  LAMBDA HANDLER
# ═══════════════════════════════════════════════════════════
def lambda_handler(event, context):
    http_method = event.get('httpMethod', '')
    raw_path    = event.get('path', '')
    qs_params   = event.get('queryStringParameters') or {}

    # CORS preflight
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': HEADERS, 'body': ''}

    try:
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])

        auth_user = require_auth(event)
        parts     = parse_path(raw_path)

        # ── Tenta rotear pelas novas rotas do Lobby ──────────────
        new_route_result = route_new_api(http_method, parts, body, qs_params, auth_user)
        if new_route_result is not None:
            return new_route_result

        # ── PUT /personagens/{id} ─────────────────────────────────
        if parts and parts[0] == 'personagens' and len(parts) == 2 and http_method == 'PUT':
            return handle_update_personagem(parts[1], body, auth_user)

        # ── Rotas antigas (retrocompatibilidade total) ────────────
        if http_method == 'GET':
            database_format = {k: [] for k in TABLE_MAPPING if k != 'users'}
            for type_key in database_format:
                try:
                    table_name = TABLE_MAPPING[type_key]
                    table = dynamodb.Table(table_name)
                    response = table.scan()
                    database_format[type_key] = response.get('Items', [])
                except Exception as e:
                    print(f"Erro ao escanear {table_name}: {e}")
            return {
                'statusCode': 200,
                'headers': HEADERS,
                'body': json.dumps(database_format, cls=DecimalEncoder)
            }

        elif http_method == 'POST':
            if '/save' in raw_path:
                item_type   = body.get('type')
                item_data   = body.get('data')
                admin_nome  = body.get('admin_nome')
                admin_senha = body.get('admin_senha')

                if not item_type or not item_data:
                    return resp(400, {'error': 'Faltando "type" ou "data"'})

                admin = validate_admin(admin_nome, admin_senha)
                if not admin:
                    return resp(403, {'error': 'Credenciais de administrador inválidas.'})

                access_level = int(admin.get('access_level', 1))

                if item_type == 'admins' and access_level != 1:
                    return resp(403, {'error': 'Somente cronistas de nível 1 podem gerenciar administradores.'})
                if access_level == 2:
                    tabs_allowed = admin.get('tabs_allowed', [])
                    if item_type not in tabs_allowed:
                        return resp(403, {'error': f'Acesso negado para "{item_type}".'})
                if access_level == 3:
                    records_allowed = admin.get('records_allowed', [])
                    if item_data.get('id', '') not in records_allowed:
                        return resp(403, {'error': 'Acesso negado para criar/editar este registro.'})

                try:
                    table = get_table(item_type)
                    table.put_item(Item=clean_item(item_data))
                    return resp(200, {'message': f'Registro salvo em {table.name}', 'item': item_data})
                except ValueError as ve:
                    return resp(400, {'error': str(ve)})

            elif '/delete' in raw_path:
                item_id     = body.get('id')
                item_nome   = body.get('nome')
                item_type   = body.get('type')
                admin_nome  = body.get('admin_nome')
                admin_senha = body.get('admin_senha')

                if not item_type:
                    return resp(400, {'error': 'Faltando "type"'})

                admin = validate_admin(admin_nome, admin_senha)
                if not admin:
                    return resp(403, {'error': 'Credenciais de administrador inválidas.'})

                access_level = int(admin.get('access_level', 1))

                if item_type == 'admins' and access_level != 1:
                    return resp(403, {'error': 'Somente nível 1 pode gerenciar admins.'})
                if access_level == 2 and item_type not in admin.get('tabs_allowed', []):
                    return resp(403, {'error': f'Acesso negado para "{item_type}".'})
                if access_level == 3:
                    return resp(403, {'error': 'Seu nível não permite excluir registros.'})

                try:
                    table = get_table(item_type)
                    key = {'nome': item_nome} if item_type == 'admins' else {'id': item_id}
                    table.delete_item(Key=key)
                    return resp(200, {'message': f'Registro excluído de {table.name}'})
                except ValueError as ve:
                    return resp(400, {'error': str(ve)})

        return resp(404, {'error': 'Rota não encontrada'})

    except Exception as e:
        print(f"Erro interno: {e}")
        return resp(500, {'error': 'Erro interno no servidor'})
