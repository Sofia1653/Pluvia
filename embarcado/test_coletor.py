import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
spec = importlib.util.spec_from_file_location('coletor', Path(__file__).resolve().parent / 'coletor.py')
coletor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coletor)

class ColetorTest(unittest.TestCase):
    def test_reconexao_reassina_topicos_e_recusa_nao_assina(self):
        client = MagicMock()
        client.subscribe.return_value = (coletor.mqtt.MQTT_ERR_SUCCESS, 1)
        coletor.on_connect(client, None, None, 1, None)
        client.subscribe.assert_not_called()
        coletor.on_connect(client, None, None, 0, None)
        coletor.on_disconnect(client, None, None, 1, None)
        coletor.on_connect(client, None, None, 0, None)
        self.assertEqual(client.subscribe.call_count, 2)
        client.subscribe.assert_called_with([(coletor.TOPICO, 0), (coletor.TOPICO_CAMERA, 0)])

    def test_leituras_invalidas_nao_interrompem_gravacao(self):
        with patch.object(coletor.psycopg, 'connect') as conectar:
            for payload in [b'{}', b'[]', b'\xff', b'{"sensor_id":"x","distancia_cm":NaN}', b'{"sensor_id":"x","distancia_cm":true}', b'{"sensor_id":"x","distancia_cm":7.5}', b'{"sensor_id":"x","distancia_cm":8}']:
                coletor.on_message(None, None, SimpleNamespace(topic='pluvia/sensor01/leituras', payload=payload))
            executar = conectar.return_value.__enter__.return_value.execute
            self.assertEqual(executar.call_count, 2)
            self.assertEqual(executar.call_args_list[0].args[1], ('x', 7.5))
            self.assertEqual(executar.call_args_list[1].args[1], ('x', 8))

    def test_camera_salva_binario_e_rejeita_payload_invalido(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(coletor, 'PASTA_IMAGENS', Path(pasta)):
            # Fixture de transporte: testa preservacao dos bytes, nao decodificacao JPEG.
            imagem = b'\xff\xd8\x00\x80\xff\xd9'
            for topico, payload in [('pluvia/sensor01/camera', imagem), ('pluvia/sensor01/camera', b'{}'), ('pluvia/../camera', imagem)]:
                coletor.on_message(None, None, SimpleNamespace(topic=topico, payload=payload))
            arquivos = list(Path(pasta).rglob('*.jpg'))
            self.assertEqual(len(arquivos), 1)
            self.assertEqual(arquivos[0].read_bytes(), imagem)
            self.assertEqual(arquivos[0].parent.name, 'sensor01')

    def test_falha_no_banco_nao_interrompe_proximas_mensagens(self):
        with patch.object(coletor.psycopg, 'connect', side_effect=[coletor.psycopg.OperationalError('falha'), unittest.mock.MagicMock()]) as conectar:
            msg = SimpleNamespace(topic='pluvia/sensor01/leituras', payload=b'{"sensor_id":"x","distancia_cm":8}')
            coletor.on_message(None, None, msg)
            coletor.on_message(None, None, msg)
            self.assertEqual(conectar.call_count, 2)

    def test_falha_de_gravacao_descarta_leitura_e_proxima_consegue_gravar(self):
        with patch.object(coletor.psycopg, 'connect') as conectar:
            conn = conectar.return_value.__enter__.return_value
            conn.execute.side_effect = [coletor.psycopg.OperationalError('banco indisponivel'), None]
            msg = SimpleNamespace(topic='pluvia/sensor01/leituras', payload=b'{"sensor_id":"x","distancia_cm":8}')
            coletor.on_message(None, None, msg)
            coletor.on_message(None, None, msg)
            self.assertEqual(conn.execute.call_count, 2)

if __name__ == '__main__':
    unittest.main()
