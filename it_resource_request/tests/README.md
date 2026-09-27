# Tests

`test_it_resource_request.py` walks a request from submit to return, checks both approval levels, classifies a third-party reply, loads demo data with and without mail, checks the three visibility levels, and checks that the access list writes the right groups.

SMTP is not contacted. Email inbox replaces the connection while tests run.

```bash
odoo -d odoo14 -u it_resource_request --test-enable --stop-after-init --no-http
```

A failed test rolls the module update back. The web service is restarted only after a run with zero failures.

---

# Testes

`test_it_resource_request.py` percorre um pedido do envio até a devolução, confere os dois níveis de aprovação, classifica uma resposta de terceiro, carrega a demonstração com e sem e-mail, confere os três níveis de visão e confere se a lista de acessos grava os grupos certos.

O SMTP não é contatado. O Email inbox troca a conexão enquanto os testes rodam.

```bash
odoo -d odoo14 -u it_resource_request --test-enable --stop-after-init --no-http
```

Um teste que falha desfaz a atualização do módulo. O serviço web só é reiniciado depois de uma execução com zero falhas.
