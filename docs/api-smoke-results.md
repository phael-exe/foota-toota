# Resultados dos smoke tests da Big Balls Data

Testes executados em 27 de agosto de 2026 contra a API de produção. Nenhuma
chave, informação da conta ou identificação de requisição foi registrada neste
documento.

Os resultados representam o comportamento observado nessa data e podem mudar
quando a cobertura do provedor for atualizada.

## Resumo

| Teste | Resultado observado |
| --- | --- |
| Autenticação em `/v1/user/me` | Sucesso; a chave foi aceita. |
| Partidas com `sport=football`, `league=epl` e `limit=10` | Sucesso; dez partidas agendadas foram retornadas. |
| Busca por `Kylian Mbappe` | Jogador encontrado. |
| Busca por `Lamine Yamal` | Jogador encontrado. |
| Busca por `Vini Jr` | Nenhum resultado. |
| Busca por `Vinicius` | Vinícius Júnior apareceu como primeiro resultado. |
| Busca por Real Madrid | Clube encontrado. |
| Busca por Barcelona | Clube encontrado. |
| Partidas do Real Madrid entre EPL, La Liga e Champions | 34 partidas encontradas. |

## Pontos encontrados

### Detalhes de jogadores

As consultas a `/v1/players/{id}?sport=football` para Mbappé, Lamine Yamal e
Vinícius Júnior responderam com HTTP 200, mas sem cobertura:

```json
{
  "data": {
    "players": null,
    "stats": null
  },
  "meta": {
    "coverage": false,
    "message": "No data available for this sport/league combination yet."
  },
  "error": null
}
```

Essas chamadas levaram aproximadamente de 40 a 60 segundos. Por isso, foram
removidas dos smoke tests rápidos.

### Detalhes de clubes

As consultas a `/v1/teams/{id}?sport=football` para Real Madrid e Barcelona
responderam com HTTP 200, mas com `stats: null` e `coverage: false`. A consulta
do Real Madrid levou cerca de 17 segundos. Essas chamadas também foram removidas
dos smoke tests rápidos.

### Filtro de liga na listagem de clubes

A consulta `/v1/teams?sport=football&league=laliga&limit=200` retornou zero
resultados. Sem o filtro `league`, a API informou 256 clubes de futebol e
encontrou Real Madrid e Barcelona normalmente. O script passou a percorrer essa
listagem paginada.

### Busca pelo nome Vini Jr

O termo `Vini Jr` retornou uma lista vazia. O termo `Vinicius` retornou três
resultados, com Vinícius Júnior na primeira posição.

### Cruzamento de partidas por clube

O teste `make test-club-matches` consultou os códigos `epl`, `laliga` e `ucl`,
unificou as partidas e filtrou pelo Real Madrid. A execução levou cerca de 3,5
segundos e encontrou:

| Competição | Partidas |
| --- | ---: |
| English Premier League | 0 |
| La Liga | 20 |
| UEFA Champions League | 14 |
| **Total** | **34** |

A ausência de partidas na EPL é o resultado esperado para o Real Madrid. O
teste demonstrou que é possível cruzar um clube entre competições usando as
partidas, mesmo quando o endpoint de detalhes do clube não possui cobertura.

Sem o parâmetro `SEASON`, a API retornou jogos da Champions 2025–26 e da La Liga
2026–27 na mesma consulta. Para análises comparáveis, o consumidor deve informar
uma temporada explicitamente ou separar os resultados por temporada.

Os objetos `home` e `away` observados continham nome, abreviação e logo, mas não
um ID de clube. O teste usa uma comparação de nomes sem diferenciar maiúsculas e
minúsculas. Esse mecanismo é suficiente para o smoke test, mas um relacionamento
de produção deve usar IDs estáveis para evitar colisões e mudanças de nome.

## Questões para discutir com o time ou com o provedor

- Existe previsão de cobertura de detalhes e estatísticas para jogadores e
  clubes de futebol?
- A ausência de cobertura pode responder mais rapidamente, sem aguardar de 17 a
  60 segundos?
- Qual valor o filtro `league` de `/v1/teams` espera para a La Liga?
- A busca de jogadores pode aceitar aliases conhecidos, como `Vini Jr`?
