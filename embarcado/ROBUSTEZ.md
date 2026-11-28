# Robustez e recuperação de leituras

## Comportamento atual

Mensagens inválidas são rejeitadas sem parar o coletor. Após falha de conexão ou execução no PostgreSQL, a leitura é perdida, o erro é registrado e a próxima mensagem tenta novamente. O cliente MQTT tenta reconectar e volta a assinar após conexão bem-sucedida. As leituras publicadas durante uma interrupção podem ser perdidas: o firmware publica em QoS 0, não mantém fila local e não possui timestamp próprio. A imagem é gravada em disco, não em `fotos_sensor`.

Os testes unitários simulam desconexão e retorno do callback, mensagens inválidas e falha do banco; não substituem a interrupção real de broker e banco. Para teste com serviços reais use `python -m unittest embarcado.test_integracao_mqtt -v`, com `PLUVIA_TEST_DB_URL` apontando para um banco de teste e `PLUVIA_TEST_BROKER`/`PLUVIA_TEST_BROKER_PORTA` se necessário. Esse teste grava e apaga dados associados a um identificador aleatório.

## Proposta de recuperação, ainda não implementada

1. Atribuir um UUID por leitura no dispositivo e registrar também a hora de medição sincronizada; tratar explicitamente relógio indisponível. Uma chave única no PostgreSQL e `INSERT ... ON CONFLICT DO NOTHING` evitariam duplicatas após uma confirmação perdida.
2. Persistir cada leitura recebida em uma fila local durável (por exemplo SQLite em volume Docker) antes de confirmar sua entrega, e ter um trabalhador que reenvie em lotes com espera crescente e limite de tamanho. Remover da fila apenas após o commit no PostgreSQL. Testar reinício entre commit e remoção, disco cheio, corrupção, falhas prolongadas e retomada sem novas mensagens.
3. Para cobrir a queda do broker, a placa também precisa de fila persistente e política para falta de espaço; QoS 1 com sessão persistente e broker configurado para persistência melhora a entrega, mas sozinho não garante dados gerados enquanto a placa está desconectada. Definir o ciclo de confirmação de ponta a ponta antes de mudar QoS, para não confirmar antes de persistir.
4. Expor contagem e idade das pendências, falhas e descarte por falta de espaço. Definir limites, retenção, sincronização e testes de carga conforme os recursos da placa e do computador.

A fila não foi ativada nesta versão: sua semântica de confirmação, migração de banco, capacidade e testes reais precisam ser acordados e validados juntos para evitar falsa garantia ou duplicação de dados.
