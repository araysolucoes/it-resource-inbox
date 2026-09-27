# Models

Python models for the mailbox.

- `email_account.py` is one mailbox: provider, SMTP, POP3, and the link to Odoo's `ir.mail_server` and `fetchmail.server`. Create and write copy the servers. The incoming server stays in draft so the fetchmail cron does not download the same box.
- `email_message.py` is one stored message, incoming or outgoing, plus the plain preview and the split between the new reply and the quoted history.
- `email_template.py` is a reusable subject and body. `{{{name}}}` is a variable. `send` and `send_for` are the calls other modules use.
- `__init__.py` loads those models. The UIDL model lives at the bottom of `email_account.py` and remembers POP3 identifiers already downloaded.

Do not print passwords in logs. Password fields are limited to the manager group.

## How to use from another module

```python
account = self.env['email.account'].get_default_account()
account.send_for_record('res.partner', partner.id, 'person@example.com', 'Subject', 'Body')
```

Or, with a template code:

```python
self.env['email.template'].send('support_reply', record, {'name': record.name})
```

---

# Modelos

Modelos Python da caixa.

- `email_account.py` é uma caixa: provedor, SMTP, POP3 e o vínculo com `ir.mail_server` e `fetchmail.server` do Odoo. Criar e gravar copiam os servidores. A entrada fica em rascunho para o cron do fetchmail não baixar a mesma caixa.
- `email_message.py` é uma mensagem gravada, de entrada ou de saída, com a prévia em texto e a separação entre a resposta nova e o histórico citado.
- `email_template.py` é assunto e corpo reutilizáveis. `{{{name}}}` é uma variável. `send` e `send_for` são as chamadas que os outros módulos usam.
- `__init__.py` carrega esses modelos. O modelo de UIDL fica no fim de `email_account.py` e lembra os identificadores POP3 já baixados.

Não registre senhas em log. Os campos de senha ficam no grupo gestor.

## Como usar a partir de outro módulo

```python
account = self.env['email.account'].get_default_account()
account.send_for_record('res.partner', partner.id, 'person@example.com', 'Subject', 'Body')
```

Ou, com o código de um modelo:

```python
self.env['email.template'].send('support_reply', record, {'name': record.name})
```
