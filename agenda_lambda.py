import json
import os
import time
import random
import string
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

dynamodb = boto3.resource('dynamodb')

TABLE_ADMINS   = os.environ.get('TABLE_AGENDA_ADMINS',   'agenda_admins')
TABLE_MESAS    = os.environ.get('TABLE_AGENDA_MESAS',    'agenda_mesas')
TABLE_SESSIONS = os.environ.get('TABLE_AGENDA_SESSIONS', 'agenda_sessions')
TABLE_PLAYERS  = os.environ.get('TABLE_AGENDA_PLAYERS',  'agenda_players')
TABLE_CONFIG   = os.environ.get('TABLE_AGENDA_CONFIG',   'agenda_config')

OMEGA_CODE         = 'omega'
DEFAULT_OMEGA_PWD  = 'omega123'

admins_tbl   = dynamodb.Table(TABLE_ADMINS)
mesas_tbl    = dynamodb.Table(TABLE_MESAS)
sessions_tbl = dynamodb.Table(TABLE_SESSIONS)
players_tbl  = dynamodb.Table(TABLE_PLAYERS)
config_tbl   = dynamodb.Table(TABLE_CONFIG)

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,DELETE',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
}


def resp(status, body):
    return {'statusCode': status, 'headers': CORS_HEADERS, 'body': json.dumps(body, cls=DecimalEncoder)}


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items() if v is not None and v != ''}
    if isinstance(obj, list):
        return [clean(i) for i in obj]
    return obj


def gen_id(prefix):
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{prefix}_{int(time.time())}_{suffix}"


def get_omega_pwd():
    try:
        r = config_tbl.get_item(Key={'key': 'omega_pwd'})
        return r.get('Item', {}).get('value', DEFAULT_OMEGA_PWD)
    except Exception:
        return DEFAULT_OMEGA_PWD


def auth_role(headers, body=None):
    """Returns ('omega'|'admin'|None, admin_item|None).
    Checks Authorization header (code:pwd) OR body fields _code/_pwd.
    """
    code, pwd = '', ''

    # 1) Authorization header: "code:password"
    auth = (headers.get('Authorization') or headers.get('authorization') or '').strip()
    if auth:
        parts = auth.split(':', 1)
        code = parts[0].strip().lower()
        pwd  = parts[1].strip() if len(parts) > 1 else ''

    # 2) Fallback: body fields _code / _pwd
    if not code and body:
        code = str(body.get('_code') or '').strip().lower()
        pwd  = str(body.get('_pwd')  or '').strip()

    if not code:
        return None, None

    if code == OMEGA_CODE:
        return ('omega', None) if pwd == get_omega_pwd() else (None, None)

    r = admins_tbl.get_item(Key={'code': code})
    admin = r.get('Item')
    if admin and admin.get('password') == pwd:
        return 'admin', admin
    return None, None


def lambda_handler(event, context):
    try:
        if 'requestContext' in event and 'http' in event.get('requestContext', {}):
            method = event['requestContext']['http']['method']
            path   = event.get('rawPath', '')
        else:
            method = event.get('httpMethod', '')
            path   = event.get('path', '')

        headers = event.get('headers') or {}
        body    = {}

        if method == 'OPTIONS':
            return resp(200, 'OK')

        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except Exception:
                return resp(400, {'message': 'JSON inválido.'})

        # ── GET /agenda/data ─────────────────────────────────────────
        # Public — returns all mesas/sessions/players/admins (passwords stripped)
        if method == 'GET' and path == '/agenda/data':
            admins_r   = admins_tbl.scan()
            mesas_r    = mesas_tbl.scan()
            sessions_r = sessions_tbl.scan()
            players_r  = players_tbl.scan()

            admins = {}
            for a in admins_r.get('Items', []):
                safe = {k: v for k, v in a.items() if k != 'password'}
                admins[a['code']] = safe

            return resp(200, {
                'admins':   admins,
                'mesas':    {m['id']:   m for m in mesas_r.get('Items', [])},
                'sessions': {s['id']:   s for s in sessions_r.get('Items', [])},
                'players':  {p['code']: p for p in players_r.get('Items', [])},
            })

        # ── GET /agenda/session/{id} ─────────────────────────────────
        # Public — used by voting screen (no auth)
        if method == 'GET' and path.startswith('/agenda/session/'):
            sess_id = path.split('/')[-1]
            r = sessions_tbl.get_item(Key={'id': sess_id})
            if 'Item' not in r:
                return resp(404, {'message': 'Sessão não encontrada.'})
            s = r['Item']
            mesa_r = mesas_tbl.get_item(Key={'id': s.get('mesaId', '')})
            return resp(200, {'session': s, 'mesa': mesa_r.get('Item', {})})

        # ── POST /agenda/vote ────────────────────────────────────────
        # Public — player submits vote (validated by playerCodes membership)
        if method == 'POST' and path == '/agenda/vote':
            sess_id     = body.get('sessionId')
            player_code = body.get('playerCode')
            date        = body.get('date')
            time_val    = body.get('time')
            if not all([sess_id, player_code, date, time_val]):
                return resp(400, {'message': 'Dados incompletos.'})
            r = sessions_tbl.get_item(Key={'id': sess_id})
            if 'Item' not in r:
                return resp(404, {'message': 'Sessão não encontrada.'})
            s = r['Item']
            mesa_r = mesas_tbl.get_item(Key={'id': s.get('mesaId', '')})
            mesa = mesa_r.get('Item', {})
            if player_code not in (mesa.get('playerCodes') or []):
                return resp(403, {'message': 'Código não pertence a esta mesa.'})
            votes = s.get('votes') or {}
            votes[player_code] = {'date': date, 'time': time_val}
            s['votes'] = votes
            sessions_tbl.put_item(Item=clean(s))
            return resp(200, {'message': 'Voto registrado.'})

        # ── POST /agenda/admin ───────────────────────────────────────
        if method == 'POST' and path == '/agenda/admin':
            role, _ = auth_role(headers, body)
            if role != 'omega':
                return resp(403, {'message': 'Apenas Omega Admin.'})
            code = body.get('code', '').strip().lower()
            if not code:
                return resp(400, {'message': 'Código obrigatório.'})
            admins_tbl.put_item(Item=clean(body))
            return resp(200, {'message': 'Admin salvo.'})

        # ── DELETE /agenda/admin/{code} ──────────────────────────────
        if method == 'DELETE' and path.startswith('/agenda/admin/'):
            role, _ = auth_role(headers, body)
            if role != 'omega':
                return resp(403, {'message': 'Apenas Omega Admin.'})
            code = path.split('/')[-1]
            admins_tbl.delete_item(Key={'code': code})
            return resp(200, {'message': 'Admin removido.'})

        # ── POST /agenda/mesa ────────────────────────────────────────
        if method == 'POST' and path == '/agenda/mesa':
            role, admin = auth_role(headers, body)
            if not role:
                return resp(403, {'message': 'Não autorizado.'})
            if role == 'admin':
                mesa_id = body.get('id')
                if not mesa_id:
                    return resp(403, {'message': 'Apenas Omega Admin pode criar mesas.'})
                ex_r = mesas_tbl.get_item(Key={'id': mesa_id})
                ex = ex_r.get('Item', {})
                if ex.get('masterId') != admin.get('code'):
                    return resp(403, {'message': 'Sem permissão para esta mesa.'})
            mesa_id = body.get('id') or gen_id('mesa')
            body['id'] = mesa_id
            mesas_tbl.put_item(Item=clean(body))
            return resp(200, {'message': 'Mesa salva.', 'id': mesa_id})

        # ── DELETE /agenda/mesa/{id} ─────────────────────────────────
        if method == 'DELETE' and path.startswith('/agenda/mesa/'):
            role, _ = auth_role(headers, body)
            if role != 'omega':
                return resp(403, {'message': 'Apenas Omega Admin.'})
            mesa_id = path.split('/')[-1]
            mesas_tbl.delete_item(Key={'id': mesa_id})
            # Cascade: delete all sessions of this mesa
            scan_r = sessions_tbl.scan(FilterExpression=Attr('mesaId').eq(mesa_id))
            with sessions_tbl.batch_writer() as bw:
                for s in scan_r.get('Items', []):
                    bw.delete_item(Key={'id': s['id']})
            return resp(200, {'message': 'Mesa e sessões removidas.'})

        # ── POST /agenda/session ─────────────────────────────────────
        if method == 'POST' and path == '/agenda/session':
            role, admin = auth_role(headers, body)
            if not role:
                return resp(403, {'message': 'Não autorizado.'})
            if role == 'admin':
                mesa_r = mesas_tbl.get_item(Key={'id': body.get('mesaId', '')})
                mesa = mesa_r.get('Item', {})
                if mesa.get('masterId') != admin.get('code'):
                    return resp(403, {'message': 'Sem permissão para esta mesa.'})
            sess_id = body.get('id') or gen_id('sess')
            body['id'] = sess_id
            sessions_tbl.put_item(Item=clean(body))
            return resp(200, {'message': 'Sessão salva.', 'id': sess_id})

        # ── DELETE /agenda/session/{id} ──────────────────────────────
        if method == 'DELETE' and path.startswith('/agenda/session/'):
            role, admin = auth_role(headers, body)
            if not role:
                return resp(403, {'message': 'Não autorizado.'})
            sess_id = path.split('/')[-1]
            if role == 'admin':
                r = sessions_tbl.get_item(Key={'id': sess_id})
                s = r.get('Item', {})
                mesa_r = mesas_tbl.get_item(Key={'id': s.get('mesaId', '')})
                mesa = mesa_r.get('Item', {})
                if mesa.get('masterId') != admin.get('code'):
                    return resp(403, {'message': 'Sem permissão.'})
            sessions_tbl.delete_item(Key={'id': sess_id})
            return resp(200, {'message': 'Sessão removida.'})

        # ── POST /agenda/player ──────────────────────────────────────
        if method == 'POST' and path == '/agenda/player':
            role, _ = auth_role(headers, body)
            if not role:
                return resp(403, {'message': 'Não autorizado.'})
            code = body.get('code', '').strip().lower()
            if not code:
                return resp(400, {'message': 'Código obrigatório.'})
            players_tbl.put_item(Item=clean(body))
            return resp(200, {'message': 'Jogador salvo.'})

        # ── DELETE /agenda/player/{code} ─────────────────────────────
        if method == 'DELETE' and path.startswith('/agenda/player/'):
            role, _ = auth_role(headers, body)
            if not role:
                return resp(403, {'message': 'Não autorizado.'})
            code = path.split('/')[-1]
            players_tbl.delete_item(Key={'code': code})
            return resp(200, {'message': 'Jogador removido.'})

        # ── POST /agenda/omega-pwd ───────────────────────────────────
        if method == 'POST' and path == '/agenda/omega-pwd':
            role, _ = auth_role(headers, body)
            if role != 'omega':
                return resp(403, {'message': 'Apenas Omega Admin.'})
            new_pwd = body.get('password', '').strip()
            if not new_pwd:
                return resp(400, {'message': 'Senha obrigatória.'})
            config_tbl.put_item(Item={'key': 'omega_pwd', 'value': new_pwd})
            return resp(200, {'message': 'Senha Omega alterada.'})

        return resp(404, {'message': 'Rota não encontrada.'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return resp(500, {'message': f'Erro interno: {str(e)}'})


# ── Setup instructions ────────────────────────────────────────────────────────
# DynamoDB tables needed (all with On-Demand billing):
#   agenda_admins   — PK: code (String)
#   agenda_mesas    — PK: id   (String)
#   agenda_sessions — PK: id   (String)
#   agenda_players  — PK: code (String)
#   agenda_config   — PK: key  (String)
#
# Lambda env vars (optional, defaults shown):
#   TABLE_AGENDA_ADMINS   = agenda_admins
#   TABLE_AGENDA_MESAS    = agenda_mesas
#   TABLE_AGENDA_SESSIONS = agenda_sessions
#   TABLE_AGENDA_PLAYERS  = agenda_players
#   TABLE_AGENDA_CONFIG   = agenda_config
#
# API Gateway routes (all pointing to this Lambda):
#   GET    /agenda/data
#   GET    /agenda/session/{id}
#   POST   /agenda/vote
#   POST   /agenda/admin
#   DELETE /agenda/admin/{code}
#   POST   /agenda/mesa
#   DELETE /agenda/mesa/{id}
#   POST   /agenda/session
#   DELETE /agenda/session/{id}
#   POST   /agenda/player
#   DELETE /agenda/player/{code}
#   POST   /agenda/omega-pwd
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Quick local test
    ev = {'httpMethod': 'GET', 'path': '/agenda/data', 'headers': {}, 'body': None}
    print(lambda_handler(ev, None))
