import json
import boto3
import os
from botocore.exceptions import ClientError

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
                'body': json.dumps(database_format)
            }
            
        elif http_method == 'POST':
            # API Gateway envia o corpo da requisição como uma string JSON
            body = json.loads(event.get('body', '{}'))
            
            if '/save' in path:
                item_type = body.get('type')
                item_data = body.get('data')
                
                if not item_type or not item_data:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Faltando "type" ou "data" no corpo da requisição'})
                    }
                
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
                
                if not item_type:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Faltando "type" para exclusão'})
                    }
                    
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
