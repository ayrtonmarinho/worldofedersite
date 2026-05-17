import json
import os
import uuid
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


dynamodb = boto3.resource('dynamodb')

TABLE_MAPS     = os.environ.get('TABLE_TB_MAPS',     'RPG_TB_Maps')
TABLE_ELEMENTS = os.environ.get('TABLE_TB_ELEMENTS', 'RPG_TB_Elements')
TABLE_SESSIONS = os.environ.get('TABLE_TB_SESSIONS', 'RPG_TB_Sessions')

maps_table     = dynamodb.Table(TABLE_MAPS)
elements_table = dynamodb.Table(TABLE_ELEMENTS)
sessions_table = dynamodb.Table(TABLE_SESSIONS)

ADMIN_SECRET = "skillarte"


def _resp(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT,DELETE',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def _auth(headers):
    h = headers or {}
    v = h.get('Authorization') or h.get('authorization', '')
    return v == ADMIN_SECRET


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items() if v is not None and v != ''}
    if isinstance(obj, list):
        return [clean(i) for i in obj]
    return obj


def lambda_handler(event, context):
    try:
        # Suporte a REST API (v1) e HTTP API (v2)
        if 'requestContext' in event and 'http' in event.get('requestContext', {}):
            # HTTP API v2
            method = event['requestContext']['http']['method']
            path   = event.get('rawPath', '')
        else:
            # REST API v1
            method = event.get('httpMethod', '')
            path   = event.get('path', '')

        headers = event.get('headers') or {}
        body    = {}

        if method == 'OPTIONS':
            return _resp(200, 'OK')

        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except Exception:
                return _resp(400, {'message': 'Body inválido — JSON esperado.'})

        # ── MAPS ──────────────────────────────────────────────────────────────

        # GET /tb/maps → listar todos os mapas (id + name resumido)
        if method == 'GET' and path == '/tb/maps':
            resp = maps_table.scan()
            maps = []
            for item in resp.get('Items', []):
                maps.append({
                    'map_id':   item['map_id'],
                    'name':     item.get('name', item['map_id']),
                    'cols':     item.get('cols', 20),
                    'rows':     item.get('rows', 15),
                    'hex_size': item.get('hex_size', 48)
                })
            return _resp(200, maps)

        # GET /tb/map/{id} → dados completos de um mapa
        elif method == 'GET' and path.startswith('/tb/map/'):
            map_id = path.split('/')[-1]
            resp = maps_table.get_item(Key={'map_id': map_id})
            if 'Item' not in resp:
                return _resp(404, {'message': 'Mapa não encontrado.'})
            return _resp(200, resp['Item'])

        # POST /tb/map → criar / sobrescrever mapa (admin)
        elif method == 'POST' and path == '/tb/map':
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            map_id = body.get('map_id') or str(uuid.uuid4())[:8]
            item = {
                'map_id':    map_id,
                'name':      body.get('name', 'Novo Mapa'),
                'bg_url':    body.get('bg_url', ''),
                'cols':      int(body.get('cols', 20)),
                'rows':      int(body.get('rows', 15)),
                'hex_size':  int(body.get('hex_size', 48)),
                'collision': body.get('collision', {}),
                'fog':       body.get('fog', {})
            }
            maps_table.put_item(Item=clean(item))
            return _resp(200, {'message': 'Mapa salvo.', 'map_id': map_id})

        # DELETE /tb/map/{id}
        elif method == 'DELETE' and path.startswith('/tb/map/'):
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            map_id = path.split('/')[-1]
            maps_table.delete_item(Key={'map_id': map_id})
            return _resp(200, {'message': f"Mapa '{map_id}' removido."})

        # ── ELEMENTS ──────────────────────────────────────────────────────────

        # GET /tb/elements → listar todos os elementos da biblioteca
        elif method == 'GET' and path == '/tb/elements':
            resp = elements_table.scan()
            return _resp(200, resp.get('Items', []))

        # POST /tb/element → criar / atualizar elemento (admin)
        elif method == 'POST' and path == '/tb/element':
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            elem_id = body.get('element_id') or str(uuid.uuid4())[:8]
            item = {
                'element_id': elem_id,
                'type':       body.get('type', 'npc'),   # npc | player | obstacle
                'name':       body.get('name', 'Elemento'),
                'image_url':  body.get('image_url', ''),
                'color':      body.get('color', '#6366f1'),
                'hp_max':     int(body.get('hp_max', 10)),
                'mana_max':   int(body.get('mana_max', 0)),
                'movement':   int(body.get('movement', 3)),
                'initiative': int(body.get('initiative', 0))
            }
            elements_table.put_item(Item=clean(item))
            return _resp(200, {'message': 'Elemento salvo.', 'element_id': elem_id})

        # DELETE /tb/element/{id}
        elif method == 'DELETE' and path.startswith('/tb/element/'):
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            elem_id = path.split('/')[-1]
            elements_table.delete_item(Key={'element_id': elem_id})
            return _resp(200, {'message': f"Elemento '{elem_id}' removido."})

        # ── SESSIONS ──────────────────────────────────────────────────────────

        # GET /tb/sessions → listar sessões ativas (admin)
        elif method == 'GET' and path == '/tb/sessions':
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            resp = sessions_table.scan()
            sessions = []
            for item in resp.get('Items', []):
                sessions.append({
                    'session_id':    item['session_id'],
                    'name':          item.get('name', item['session_id']),
                    'map_id':        item.get('map_id', ''),
                    'current_turn':  item.get('current_turn', 0),
                    'player_count':  len(item.get('tokens', []))
                })
            return _resp(200, sessions)

        # POST /tb/session → criar nova sessão (admin)
        elif method == 'POST' and path == '/tb/session':
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            sess_id = body.get('session_id') or str(uuid.uuid4())[:8]
            item = {
                'session_id':      sess_id,
                'name':            body.get('name', 'Nova Sessão'),
                'map_id':          body.get('map_id', ''),
                'tokens':          body.get('tokens', []),
                'initiative_order': body.get('initiative_order', []),
                'current_turn':    int(body.get('current_turn', 0)),
                'fog_revealed':    body.get('fog_revealed', {}),
                'paused':          body.get('paused', False)
            }
            sessions_table.put_item(Item=clean(item))
            return _resp(200, {'message': 'Sessão criada.', 'session_id': sess_id})

        # GET /tb/session/{id} → estado completo da sessão (polling dos jogadores)
        elif method == 'GET' and path.startswith('/tb/session/'):
            sess_id = path.split('/')[-1]
            resp = sessions_table.get_item(Key={'session_id': sess_id})
            if 'Item' not in resp:
                return _resp(404, {'message': 'Sessão não encontrada.'})
            return _resp(200, resp['Item'])

        # POST /tb/session/{id}/update → atualizar estado da sessão
        # Usado tanto pelo GM (qualquer campo) quanto pelo jogador (mover seu token)
        elif method == 'POST' and path.endswith('/update'):
            parts = path.split('/')
            # path = /tb/session/{id}/update
            sess_id = parts[-2]

            resp = sessions_table.get_item(Key={'session_id': sess_id})
            if 'Item' not in resp:
                return _resp(404, {'message': 'Sessão não encontrada.'})

            session = resp['Item']

            # Jogador movendo seu próprio token: body tem token_id, q, r, player_name
            if 'token_id' in body and 'q' in body and 'r' in body:
                tokens = session.get('tokens', [])
                token_idx = next((i for i, t in enumerate(tokens) if t.get('token_id') == body['token_id']), None)
                if token_idx is None:
                    return _resp(404, {'message': 'Token não encontrado na sessão.'})
                tokens[token_idx]['q'] = int(body['q'])
                tokens[token_idx]['r'] = int(body['r'])
                if 'hp' in body:
                    tokens[token_idx]['hp'] = int(body['hp'])
                session['tokens'] = tokens
                sessions_table.put_item(Item=clean(session))
                return _resp(200, {'message': 'Token movido.'})

            # Auto-sync tokens-only (GM arrastando tokens no Builder) — sem auth necessária,
            # pois session_id já é o segredo compartilhado e tokens não são dados sensíveis
            if set(body.keys()) <= {'tokens'} and 'tokens' in body:
                session['tokens'] = body['tokens']
                sessions_table.put_item(Item=clean(session))
                return _resp(200, {'message': 'Tokens sincronizados.'})

            # GM atualizando campos sensíveis da sessão (fog, initiative, paused…)
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})

            allowed = ['tokens', 'initiative_order', 'current_turn', 'fog_revealed', 'paused', 'map_id', 'name']
            for k in allowed:
                if k in body:
                    session[k] = body[k]

            sessions_table.put_item(Item=clean(session))
            return _resp(200, {'message': 'Sessão atualizada.'})

        # DELETE /tb/session/{id}
        elif method == 'DELETE' and path.startswith('/tb/session/'):
            if not _auth(headers):
                return _resp(403, {'message': 'Acesso negado.'})
            sess_id = path.split('/')[-1]
            sessions_table.delete_item(Key={'session_id': sess_id})
            return _resp(200, {'message': f"Sessão '{sess_id}' encerrada."})

        return _resp(404, {'message': 'Rota não encontrada.'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _resp(500, {'message': f'Erro interno: {str(e)}'})


# ── Testes locais ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(lambda_handler({'httpMethod': 'GET', 'path': '/tb/maps', 'headers': {}}, None))
