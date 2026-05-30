import json
import os
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


# Inicializar os mapeamentos de recursos do serviço DynamoDB
dynamodb = boto3.resource('dynamodb')

# Tentar buscar nome das tabelas por variáveis de ambiente AWS.
# Adicionado fallback para nomes de teste (ex: RPG_Users) caso as Serverless envs não existam agora
TABLE_USERS_NAME = os.environ.get('TABLE_USERS', 'RPG_Users')
TABLE_TREE_NAME  = os.environ.get('TABLE_TREE',  'RPG_Tree')

users_table = dynamodb.Table(TABLE_USERS_NAME)
tree_table  = dynamodb.Table(TABLE_TREE_NAME)

# Chave reservada na RPG_Tree para o registro global de keywords
KEYWORDS_KEY = 'WOE_KEYWORDS'

# "Senha" simples fixada estaticamente pra validação e segurança em rotas admin.
ADMIN_SECRET = "skillarte"


def _build_response(status_code, body):
    """
    Empacota a resposta no formato que o API Gateway espera no Proxy Integration.
    Inclui os HEADERS de liberação de CORS (Access-Control-Allow).
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            # Essencial para funcionar chamadas direto do navegador
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT,DELETE',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def check_admin_auth(headers):
    """Verifica se o header de autorização existe e valida se a senha consta com o segredo"""
    # A AWS pode repassar headers em minúsculas ou capitalizados.
    auth_header = headers.get('Authorization') or headers.get('authorization')
    if auth_header == ADMIN_SECRET:
        return True
    return False


def lambda_handler(event, context):
    """
    Função principal e porta de entrada (Handler) na AWS.
    Recebe os eventos gerados através de integrações tipo HTTP.
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        headers = event.get('headers', {})

        # Tratamento de chamada de Verificação Inicial do Navegador (CORS Preflight)
        if http_method == 'OPTIONS':
            return _build_response(200, "OK")

        # Parsing do body text / form-data transformando pra um dicionário do Python
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])

        # ------------- ROTAS LIVRES E ACESSÍVEIS (SE TIVER ID) -------------

        # ROTA: GET /user/{code} -> Buscar o estado de atributos/árvore de um jogador único.
        if http_method == 'GET' and path.startswith('/user/'):
            user_code = path.split('/')[-1]
            try:
                response = users_table.get_item(Key={'code': user_code})
                if 'Item' in response:
                    return _build_response(200, response['Item'])
                else:
                    return _build_response(404, {"message": "Usuário não encontrado."})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: POST /user -> Criar jogador inédito ou Sobrescrever infos existentes simulando um SAVE.
        # Tanto o próprio usuário salvando quanto o Admin concedendo pontos caem nesta mesma rota.
        elif http_method == 'POST' and path == '/user':
            user_code = body.get('code')
            if not user_code:
                return _build_response(400, {"message": "Campo 'code' é obrigatório no corpo do JSON."})

            try:
                # O body inteiro recebido do HTML substitui os campos base
                users_table.put_item(Item=body)
                return _build_response(200, {"message": "Personagem/Usuário salvo com sucesso.", "UserCode": user_code})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA LER ARVORE ATIVA (Aberto)
        elif http_method == 'GET' and path == '/tree':
            try:
                config_resp = tree_table.get_item(
                    Key={'tree_id': 'SYSTEM_CONFIG'})
                active_id = config_resp.get('Item', {}).get(
                    'active_tree_id', 'global_tree')

                response = tree_table.get_item(Key={'tree_id': active_id})
                if 'Item' in response:
                    # Envolve a resposta para o front saber qual o ID ativo carregou
                    return _build_response(200, {
                        'tree_id': active_id,
                        'name': response['Item'].get('name', 'Árvore Ativa'),
                        'data': response['Item']['data']
                    })
                else:
                    return _build_response(404, {"message": f"Árvore '{active_id}' não encontrada no Banco."})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: GET /keywords -> Retorna todas as keywords globais (aberto — players precisam pra renderizar stats)
        elif http_method == 'GET' and path == '/keywords':
            try:
                response = tree_table.get_item(Key={'tree_id': KEYWORDS_KEY})
                if 'Item' in response:
                    return _build_response(200, {'keywords': response['Item'].get('keywords', {})})
                return _build_response(200, {'keywords': {}})
            except ClientError as e:
                return _build_response(500, {'message': str(e)})

        # ROTA: POST /keywords -> Salva o mapa completo de keywords (Admin)
        elif http_method == 'POST' and path == '/keywords':
            if not check_admin_auth(headers):
                return _build_response(403, {'message': 'Acesso Administrativo Negado.'})
            keywords = body.get('keywords')
            if keywords is None:
                return _build_response(400, {'message': "Campo 'keywords' obrigatório."})
            try:
                tree_table.put_item(Item={'tree_id': KEYWORDS_KEY, 'keywords': keywords})
                return _build_response(200, {'message': 'Keywords globais salvas com sucesso.'})
            except ClientError as e:
                return _build_response(500, {'message': str(e)})

        # -------------- MÉTODOS RESTRITOS A ROOT / ADMINISTRATIVOS --------------

        # ROTA: GET /users -> Buscar TODOS os jogadores para listar as tabelas do Admin
        elif http_method == 'GET' and path == '/users':
            if not check_admin_auth(headers):
                return _build_response(403, {"message": "Acesso Administrativo Negado. Token/Senha inválidos!"})
            try:
                response = users_table.scan()
                users = response.get('Items', [])
                return _build_response(200, users)
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: GET /manage/trees -> Listar todas as árvores disponíveis no Banco (Admin)
        elif http_method == 'GET' and path == '/manage/trees':
            if not check_admin_auth(headers):
                return _build_response(403, {"message": "Negado!"})
            try:
                # Scan para obter as árvores listadas
                response = tree_table.scan()
                trees = []
                reserved = {'SYSTEM_CONFIG', KEYWORDS_KEY}
                for item in response.get('Items', []):
                    if item['tree_id'] not in reserved:
                        trees.append(
                            {'id': item['tree_id'], 'name': item.get('name', item['tree_id'])})

                # Pega a ativa pra interface saber qual marcar
                config_resp = tree_table.get_item(
                    Key={'tree_id': 'SYSTEM_CONFIG'})
                active_id = config_resp.get('Item', {}).get(
                    'active_tree_id', 'global_tree')

                return _build_response(200, {"trees": trees, "active": active_id})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA LER UMA ARVORE ESPECÍFICA (Admin)
        elif http_method == 'GET' and path.startswith('/tree/') and not path.endswith('/active'):
            target_id = path.split('/')[-1]
            try:
                response = tree_table.get_item(Key={'tree_id': target_id})
                if 'Item' in response:
                    return _build_response(200, {
                        'tree_id': target_id,
                        'name': response['Item'].get('name', target_id),
                        'data': response['Item']['data']
                    })
                return _build_response(404, {"message": "Nao encontrada."})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: POST /tree -> Salvar uma árvore específica.
        elif http_method == 'POST' and path == '/tree':
            if not check_admin_auth(headers):
                return _build_response(403, {"message": "Acesso Administrativo Negado. Edição não autorizada!"})
            try:
                # O front agora mapeia {'tree_id': 'nome', 'name': '...', 'data': { ... }}
                target_id = body.get('tree_id', 'global_tree')
                tree_name = body.get('name', target_id)
                # Fallback pra manter compativel
                tree_data = body.get('data', body)

                tree_table.put_item(
                    Item={'tree_id': target_id, 'name': tree_name, 'data': tree_data})
                return _build_response(200, {"message": f"Árvore '{target_id}' guardada na nuvem sucesso."})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: POST /manage/trees/active -> Mudar a arvore setada no momento
        elif http_method == 'POST' and path == '/manage/trees/active':
            if not check_admin_auth(headers):
                return _build_response(403, {})
            try:
                new_active = body.get('active_tree_id')
                if not new_active:
                    return _build_response(400, {"message": "Precisa fornecer active_tree_id"})

                tree_table.put_item(
                    Item={'tree_id': 'SYSTEM_CONFIG', 'active_tree_id': new_active})
                return _build_response(200, {"message": f"O Jogo inteiro agora usa a árvore {new_active}!"})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: DELETE /user/{code} -> Excluir jogador do banco (Admin)
        elif http_method == 'DELETE' and path.startswith('/user/'):
            if not check_admin_auth(headers):
                return _build_response(403, {"message": "Acesso Administrativo Negado."})
            user_code = path.split('/')[-1]
            try:
                users_table.delete_item(Key={'code': user_code})
                return _build_response(200, {"message": f"Jogador '{user_code}' removido com sucesso."})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # ROTA: DELETE /tree/{id} -> Deletar uma árvore do banco
        elif http_method == 'DELETE' and path.startswith('/tree/'):
            if not check_admin_auth(headers):
                return _build_response(403, {})
            target_id = path.split('/')[-1]
            try:
                tree_table.delete_item(Key={'tree_id': target_id})
                return _build_response(200, {"message": f"Árvore removida do banco de dados."})
            except ClientError as e:
                return _build_response(500, {"message": str(e)})

        # Rota Padrão (Sem Match)
        return _build_response(404, {"message": "Rota informada não encontrada no Gateway de APIs ou recurso desativado."})

    except Exception as e:
        # Se algo quebrar inesperadamente no pacote como tipo incompatível etc.
        import traceback
        traceback.print_exc()
        return _build_response(500, {"message": f"Erro interno (Fatal Runtime): {str(e)}"})


# -------------------------------------------------------------
# Simulação mockada local para bateria de testes rápidos locais.
# Só ativado executando pelo CMD ou na compilação do VisualStudio
if __name__ == "__main__":
    test_get_users = {
        "httpMethod": "GET",
        "path": "/users",
        "headers": {"Authorization": "skillarte"}
    }
    print("\n🚀[TESTE] GET /users (admin):")
    print(lambda_handler(test_get_users, None))

    test_get_keywords = {
        "httpMethod": "GET",
        "path": "/keywords",
        "headers": {}
    }
    print("\n🔑[TESTE] GET /keywords (público):")
    print(lambda_handler(test_get_keywords, None))

    test_post_keywords = {
        "httpMethod": "POST",
        "path": "/keywords",
        "headers": {"Authorization": "skillarte"},
        "body": json.dumps({
            "keywords": {
                "forca": {"id": "forca", "name": "Força", "colorType": "solid", "color": "#f97316"},
                "magia": {"id": "magia", "name": "Magia", "colorType": "gradient",
                          "gradStops": ["#3b82f6", "#8b5cf6"], "gradDir": "to right"}
            }
        })
    }
    print("\n🔑[TESTE] POST /keywords (admin):")
    print(lambda_handler(test_post_keywords, None))
