# Checklist atualizado — Pluvia

Atualizado em 16/11/2026 com base no código e na documentação desta cópia do repositório Pluvia, branch `integration`, commit `c9d168c`. A análise não verifica outros repositórios, serviços externos ou evidências fora desta cópia. Responsáveis e prazos devem ser combinados pelo grupo.

**Como ler:** `[x]` indica atividade com implementação ou evidência documental encontrada; `[~]` indica implementação parcial, necessidade de comprovação ou trabalho descrito como concluído pelo grupo sem evidência suficiente nesta branch; `[ ]` indica pendência. Um `[x]` no código não comprova, sozinho, que o sistema foi executado fisicamente ou que toda a entrega foi aceita. As datas abaixo são as do planejamento original; as semanas passadas não implicam que todas as tarefas foram concluídas no prazo.

**Verificação nesta cópia:** em 16/11/2026, passaram 6 testes de alerta e armazenamento simulado e 2 testes do coletor com Python 3.14. O ambiente `.venv` foi criado localmente e usa pacotes já instalados; ele não está versionado. Esses testes não comprovam funcionamento do hardware, MQTT, PostgreSQL real ou ambiente completo de ML. Comandos e dependências para os testes estão em `INTEGRACAO.md`.

## Semanas 11 e 12 — Dados, MQTT e primeira versão do modelo

- [x] Levantar e documentar dados históricos de chuva, maré e ocorrências, suas limitações e qualidade. Evidência: `relatorio_qualidade.md` e scripts `baixar_dados.py` e `baixar_local.py`.
- [x] Definir alvo e variáveis, limpar e preparar dados e realizar EDA. Evidência: `notebooks/01_eda_preparacao.ipynb` e `src/preparacao.py`.
- [~] Disponibilizar o bootstrap dataset e garantir que outra pessoa consiga reproduzi-lo: o relatório descreve o dataset, mas os CSVs `processed/` não estão versionados na branch. Documentar fontes, acesso, comandos, versões e uma amostra ou forma confiável de recriá-lo.
- [x] Definir a estrutura inicial do banco em `schema.sql`.
- [~] Configurar broker, publicação pelo ESP32 e recepção MQTT: o grupo marcou os testes como concluídos e há firmware, configuração Mosquitto e coletor. Reunir logs ou vídeo dos testes; a execução não foi verificada nesta análise.
- [~] Criar simulador MQTT: o grupo marcou como concluído, mas não há simulador identificado nesta branch. Localizar o código no outro repositório ou implementar e documentar um simulador.
- [~] Receber e persistir leituras e imagens: `embarcado/coletor.py` prevê CSV e arquivos, e PostgreSQL opcional. Demonstrar o fluxo executado e conferir os dados persistidos.
- [x] Treinar e avaliar uma primeira versão do modelo: notebooks de modelagem e relatório apresentam resultados; garantir acesso ao dataset e aos artefatos para reprodução.

## Semana 13 — Modelo e sistema embarcado

- [x] Avaliar e ajustar modelos, comparando regressão logística, floresta aleatória e gradient boosting. Evidência: `notebooks/02_modelagem_mlflow.ipynb` e `relatorio_qualidade.md`.
- [x] Definir uma primeira regra de níveis de risco e alerta combinado em `src/modelo.py` e `src/alerta.py`.
- [~] Validar os critérios de risco e calibrar os limiares do sensor (5, 15 e 30 cm) com a instalação e dados reais; os limiares atuais são provisórios.
- [~] Organizar e disponibilizar histórico de risco por região: existem dados e métricas por bairro, mas ainda é necessário persistir e consultar o histórico das inferências.
- [~] Comprovar estabilidade das leituras, chegada das mensagens e captura da câmera: o checklist original indica que foram testadas; anexar evidências, condições e resultados. O firmware e os testes de câmera existem na branch.
- [~] Integrar leituras ao banco: há código em `embarcado/armazenamento.py` e tabelas no schema, mas o próprio `INTEGRACAO.md` informa que o schema ainda precisa ser executado em PostgreSQL real.

## Semana 14 — Backend, banco e API

- [ ] Criar e configurar PostgreSQL e executar `schema.sql` em um banco vazio; corrigir problemas encontrados e documentar a inicialização.
- [~] Testar a conexão e persistência de leituras e fotos no PostgreSQL, incluindo indisponibilidade do banco e recuperação; existem código e testes simulados, mas falta comprovação com banco real.
- [~] Consolidar o processamento MQTT como serviço executável e verificar publicação, validação, gravação e reconexão. O coletor já existe.
- [ ] Criar API para consultar sensores, últimas leituras, histórico, inferências e níveis de risco; definir contratos, filtros e respostas de erro.
- [ ] Integrar a API ao modelo treinado e ao alerta combinado, com carregamento reproduzível do artefato e pré-processamento consistente.
- [ ] Testar armazenamento e consultas de ponta a ponta, incluindo dados ausentes, leitura antiga, erro de conexão e entradas inválidas.

## Semana 15 — Frontend e dashboard

- [~] Definir estrutura visual: o checklist original marca esta atividade como concluída, mas não há frontend nesta branch. Localizar e reunir o material existente no outro repositório.
- [ ] Desenvolver dashboard integrado à API/MQTT com estado dos sensores, últimas leituras, inferências, níveis de risco, horário da última atualização e falhas de comunicação.
- [ ] Implementar mapa e visualização de risco por região, usando dados disponíveis e identificando ausência ou desatualização de informação.
- [ ] Exibir histórico de leituras, inferências e alertas por região/sensor.
- [ ] Integrar a interface à API e testar carregamento, atualizações, erros e apresentação dos dados.

## Semana 16 — 16 a 22 de novembro — Embarcados e alertas

- [~] Consolidar e testar firmware do ESP32-CAM, ultrassom e câmera; o código está em `embarcado/firmware/`, mas é preciso demonstrar seu funcionamento na montagem final.
- [~] Verificar tratamento de leitura inválida e queda de conexão, envio contínuo e reconexão com testes registrados.
- [ ] Corrigir ou mapear a diferença entre `sensor_id` do payload (`PLUVIA_01`) e identificador no tópico (`sensor01`), para associar leituras e fotos.
- [~] Unificar e documentar configuração do endereço do broker, credenciais e horário: `INTEGRACAO.md` e `embarcado/README.md` descrevem configuração e horário do coletor; faltam unificar os IPs padrão e avaliar sincronização de tempo na placa.
- [~] Implementar alertas preventivos: `src/alerta.py` calcula um alerta combinado, mas ainda falta execução automática, persistência e apresentação pela solução.
- [ ] Testar o fluxo sensor ou simulador → MQTT → coletor → armazenamento → API → dashboard; documentar as evidências.
- [ ] Decidir se análise de imagens faz parte do escopo: atualmente as fotos são apenas armazenadas; não há detecção de obstruções.

## Semana 17 — 23 a 29 de novembro — Integração e validação

- [ ] Construir DAG(s) no Apache Airflow para ingestão, validação, preparação e disponibilização dos dados de treinamento; definir agendamento, dependências, logs, tratamento de falhas e reexecução.
- [ ] Automatizar o consumo de novos dados e a geração de inferências: obter as variáveis de bairro e dia necessárias ao modelo, aplicar o pré-processamento e registrar resultado, horário, versão do modelo e origem do alerta.
- [~] Definir e demonstrar como as leituras do sensor se relacionam ao modelo: `src/alerta.py` e `INTEGRACAO.md` documentam a regra do maior nível; o sensor não é variável de entrada do modelo. Falta demonstrar o fluxo exigido em execução.
- [ ] Implementar Docker Compose com broker MQTT, PostgreSQL, Airflow, MLflow, API, coletor e dashboard, além de configuração, volumes, inicialização e documentação; demonstrar a execução completa com um comando.
- [ ] Validar MQTT, banco, API, processamento, dashboard e alertas juntos, incluindo recuperação de falhas e leitura vencida.
- [~] Conferir e registrar experimentos no MLflow: os notebooks contêm chamadas de registro e o relatório descreve resultados e modelos registrados; o armazenamento `mlruns` e os modelos não estão nesta cópia. Garantir que experimentos, trials e artefatos sejam acessíveis ou reproduzíveis.
- [ ] Conferir o acesso ao modelo final e suas dependências, refazer a execução em ambiente limpo e registrar versão do dataset e do modelo.
- [~] Verificar segurança e configuração para a demonstração: há arquivo de exemplo e regras para ignorar segredos; o Mosquitto atual permite acesso anônimo e não usa TLS. Validar a configuração efetiva e o acesso aos serviços.
- [~] Corrigir problemas encontrados, guardar resultados dos testes e registrar limitações: as limitações estão em `INTEGRACAO.md` e `relatorio_qualidade.md`, e os 8 testes Python acima passaram. Faltam testes integrados e registro de suas evidências e correções.

## Semana 18 — 30 de novembro a 6 de dezembro — Status Report 2

- [~] Organizar documentação técnica: `INTEGRACAO.md`, `embarcado/README.md` e `relatorio_qualidade.md` cobrem arquitetura, configuração, testes e limitações. Completar reprodução do dataset e documentar os serviços e endpoints quando existirem.
- [~] Reunir evidências: há notebooks com resultados, relatório e testes Python executados nesta análise. Faltam reunir dados de exemplo, logs MQTT e do coletor, registros no banco, DAG executada, artefatos MLflow, resposta da API, dashboard e evidências integradas.
- [ ] Preparar slides e atualizar o Google Site com as entregas, resultados, responsáveis e limitações.
- [ ] Preparar e testar o ambiente de demonstração; deixar o simulador pronto como alternativa ao hardware.
- [ ] Ensaiar o SR2 e dividir a apresentação entre os integrantes.

## Semana 19 — 7 a 13 de dezembro — Apresentação final

- [ ] Demonstrar aquisição física ou simulada, MQTT, persistência, Airflow, MLflow, Docker Compose, API e dashboard em um fluxo integrado.
- [ ] Explicar a arquitetura, as decisões técnicas, os resultados de validação e o papel da regra que combina sensor e modelo.
- [ ] Apresentar mapa, histórico, alertas e monitoramento conforme implementados; mostrar evidências dos testes.
- [ ] Discutir limitações dos dados e do modelo, medidas de segurança e próximos passos; finalizar e organizar as entregas.

## Conferência específica dos entregáveis de Machine Learning

- [x] **Ideação e definição do problema:** os notebooks e o relatório descrevem previsão de risco de alagamento por bairro e dia. Organizar a apresentação da proposta e das decisões.
- [~] **Bootstrap e aquisição:** dados históricos e aquisição MQTT estão descritos e implementados em parte; falta garantir acesso reproduzível ao dataset e comprovar publicação, recepção e persistência em execução.
- [~] **Pipeline e EDA:** EDA e preparação estão nos notebooks e em `src/preparacao.py`; falta a orquestração automática no Airflow e sua execução demonstrada.
- [~] **Modelo baseline:** regressão logística e métricas constam dos notebooks e relatório; verificar que parâmetros, métricas e artefatos estejam efetivamente acessíveis no MLflow reproduzido.
- [~] **Três modelos e comparação:** os notebooks comparam logística, floresta e boosting, com gráficos e análise crítica; confirmar acesso aos registros e artefatos MLflow de cada experimento.
- [~] **Otimização:** o notebook usa Optuna e prevê registro dos trials no MLflow; reproduzir e conferir parâmetros, resultados e registros persistidos.
- [x] **Validação cruzada e generalização:** notebook e relatório discutem validação por ano, contraste com k-fold estratificado, estabilidade, overfitting e teste cronológico. Preservar os resultados e evidências para apresentação.
- [~] **Modelo integrado à aquisição:** existe função para combinar previsão com leitura recente, mas falta serviço automático que obtenha as variáveis necessárias, execute inferências e mostre os resultados.
- [ ] **Docker Compose:** criar ambiente reproduzível com os serviços necessários e validar inicialização por um comando.
- [ ] **Dashboard:** integrar dados de aquisição, inferências e monitoramento de execução.
- [ ] **Demonstração completa:** executar e apresentar todos os componentes integrados, com justificativas e limitações.

## Pontos de atenção para a apresentação

- O relatório descreve dados muito desbalanceados e poucos eventos independentes; a validação cronológica reportada da logística otimizada tem PR-AUC de aproximadamente 0,033. Não apresentar o resultado como garantia de previsão de todos os alagamentos.
- O sensor não foi usado para treinar o modelo; o alerta usa o maior nível entre modelo e sensor. As fotografias não são analisadas.
- Os dados usados no treino são históricos e o relatório aponta limitações de chuva, maré e registros. Documentar como serão obtidas as variáveis necessárias para uma inferência atual.
- A branch analisada não inclui o outro repositório Pluvia: atividades já feitas nele podem alterar este diagnóstico quando forem verificadas.
