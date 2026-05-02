import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import ClientError

# Encoder customizado para lidar com o tipo Decimal retornado pelo DynamoDB
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)

# Inicializa o recurso do DynamoDB
dynamodb = boto3.resource('dynamodb')

# Mapeamento dos tipos do frontend para os nomes das tabelas no DynamoDB
TABLE_MAPPING = {
    'habilidades': 'skills',
    'itens': 'itens',
    'personagens': 'characters',
    'escolas': 'schools',
    'categorias': 'categories',
    'lugares': 'places',
    'admins': 'admins',
    'treinamentos': 'trainings'
}

def get_table(type_key):
    table_name = TABLE_MAPPING.get(type_key)
    if not table_name:
        raise ValueError(f"Tipo desconhecido: {type_key}")
    return dynamodb.Table(table_name)

def validate_admin(admin_nome, admin_senha):
    """
    Busca o administrador na tabela 'admins' do DynamoDB e valida as credenciais.
    Retorna o registro do admin se válido, ou None se inválido.
    """
    if not admin_nome or not admin_senha:
        return None
    
    try:
        admins_table = dynamodb.Table('admins')
        response = admins_table.get_item(Key={'nome': admin_nome})
        admin = response.get('Item')
        
        if admin and admin.get('senha') == admin_senha:
            return admin
        return None
    except Exception as e:
        print(f"Erro ao validar admin: {str(e)}")
        return None

def lambda_handler(event, context):
    """
    Função principal do AWS Lambda que atua como proxy para o API Gateway.
    Lida com requisições GET (listar tudo), POST /save (criar/editar) e POST /delete (excluir).
    Agora utilizando múltiplas tabelas para uma arquitetura mais organizada.
    """
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    
    # Headers para permitir CORS (Crucial para chamadas do front-end no navegador)
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    
    # Lida com a requisição de Preflight do CORS (OPTIONS)
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
        
    try:
        if http_method == 'GET':
            # Prepara a estrutura de retorno baseada nas chaves que o front-end espera
            database_format = {
                'habilidades': [],
                'itens': [],
                'personagens': [],
                'escolas': [],
                'categorias': [],
                'lugares': [],
                'admins': [] # Se quiser carregar no front-end ou validar depois
            }
            
            # Faz um scan em todas as tabelas mapeadas
            # Em cenários de altíssima escala, considere usar chamadas assíncronas (asyncio) 
            # ou repensar a estratégia de carregar todo o banco na inicialização.
            for type_key, table_name in TABLE_MAPPING.items():
                try:
                    table = dynamodb.Table(table_name)
                    response = table.scan()
                    database_format[type_key] = response.get('Items', [])
                except Exception as e:
                    # Caso uma das tabelas não exista, apenas loga e continua
                    print(f"Erro ao escanear tabela {table_name}: {str(e)}")
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(database_format, cls=DecimalEncoder)
            }
            
        elif http_method == 'POST':
            # API Gateway envia o corpo da requisição como uma string JSON
            body = json.loads(event.get('body', '{}'))
            
            if '/save' in path:
                item_type = body.get('type')
                item_data = body.get('data')
                admin_nome = body.get('admin_nome')
                admin_senha = body.get('admin_senha')
                
                if not item_type or not item_data:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Faltando "type" ou "data" no corpo da requisição'})
                    }
                
                # ===== VALIDAÇÃO DE ADMIN =====
                admin = validate_admin(admin_nome, admin_senha)
                if not admin:
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Credenciais de administrador inválidas ou não fornecidas.'})
                    }
                
                access_level = admin.get('access_level', 1)
                # Converte para int caso venha como Decimal do DynamoDB
                if hasattr(access_level, '__int__'):
                    access_level = int(access_level)
                
                # Somente Level 1 pode gerenciar cronistas (admins)
                if item_type == 'admins' and access_level != 1:
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Somente cronistas de nível 1 podem gerenciar administradores.'})
                    }
                
                # Level 2: Só pode operar nas abas permitidas
                if access_level == 2:
                    tabs_allowed = admin.get('tabs_allowed', [])
                    if item_type not in tabs_allowed:
                        return {
                            'statusCode': 403,
                            'headers': headers,
                            'body': json.dumps({'error': f'Seu nível de acesso não permite operações na aba "{item_type}".'})
                        }
                
                # Level 3: Só pode EDITAR registros específicos (não pode criar novos)
                if access_level == 3:
                    records_allowed = admin.get('records_allowed', [])
                    item_id = item_data.get('id', '')
                    
                    # Verifica se o registro já existe (edição) ou é novo (criação)
                    if item_id not in records_allowed:
                        return {
                            'statusCode': 403,
                            'headers': headers,
                            'body': json.dumps({'error': 'Seu nível de acesso não permite criar registros ou editar este registro.'})
                        }
                # ===== FIM DA VALIDAÇÃO =====
                
                try:
                    table = get_table(item_type)
                    # Salva no DynamoDB (se a chave de partição já existir, ele substitui/atualiza)
                    table.put_item(Item=item_data)
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps({'message': f'Registro salvo na tabela {table.name} com sucesso', 'item': item_data})
                    }
                except ValueError as ve:
                    return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': str(ve)})}
                
            elif '/delete' in path:
                item_id = body.get('id')
                item_nome = body.get('nome')
                item_type = body.get('type')
                admin_nome = body.get('admin_nome')
                admin_senha = body.get('admin_senha')
                
                if not item_type:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Faltando "type" para exclusão'})
                    }
                
                # ===== VALIDAÇÃO DE ADMIN =====
                admin = validate_admin(admin_nome, admin_senha)
                if not admin:
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Credenciais de administrador inválidas ou não fornecidas.'})
                    }
                
                access_level = admin.get('access_level', 1)
                if hasattr(access_level, '__int__'):
                    access_level = int(access_level)
                
                # Somente Level 1 pode gerenciar cronistas (admins)
                if item_type == 'admins' and access_level != 1:
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Somente cronistas de nível 1 podem gerenciar administradores.'})
                    }
                
                # Level 2: Só pode deletar nas abas permitidas
                if access_level == 2:
                    tabs_allowed = admin.get('tabs_allowed', [])
                    if item_type not in tabs_allowed:
                        return {
                            'statusCode': 403,
                            'headers': headers,
                            'body': json.dumps({'error': f'Seu nível de acesso não permite exclusões na aba "{item_type}".'})
                        }
                
                # Level 3: NÃO pode deletar nada
                if access_level == 3:
                    return {
                        'statusCode': 403,
                        'headers': headers,
                        'body': json.dumps({'error': 'Seu nível de acesso não permite excluir registros.'})
                    }
                # ===== FIM DA VALIDAÇÃO =====
                    
                try:
                    table = get_table(item_type)
                    
                    if item_type == 'admins':
                        if not item_nome:
                            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Faltando "nome" para exclusão de admin'})}
                        key_to_delete = {'nome': item_nome}
                    else:
                        if not item_id:
                            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Faltando "id" para exclusão'})}
                        key_to_delete = {'id': item_id}

                    table.delete_item(Key=key_to_delete)
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps({'message': f'Registro excluído da tabela {table.name} com sucesso'})
                    }
                except ValueError as ve:
                    return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': str(ve)})}
                
        # Rota não encontrada
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Caminho não encontrado'})
        }
            
    except Exception as e:
        print(f"Erro Interno: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Erro interno no servidor'})
        }
