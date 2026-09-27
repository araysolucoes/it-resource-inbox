# Data

Records loaded with the module.

`ir_cron.xml` creates the scheduled action **Email: fetch POP3**. It runs `cron_fetch_all` every five minutes and only on accounts with POP enabled.

The same file calls `_sync_existing_accounts` on each module update, so mailboxes that already exist are copied into Odoo's outgoing and incoming server lists.

---

# Dados

Registros carregados com o módulo.

`ir_cron.xml` cria a ação agendada **Email: fetch POP3**. Ela roda `cron_fetch_all` a cada cinco minutos e só nas contas com POP ligado.

O mesmo arquivo chama `_sync_existing_accounts` em cada atualização do módulo, para as caixas já gravadas serem copiadas para as listas de servidor de saída e de entrada do Odoo.
