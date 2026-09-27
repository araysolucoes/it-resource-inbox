# Tests

`test_email_inbox.py` checks send, POP3 replies, the Gmail `recent:` login, provider presets, the HTML template, the clean preview, and the link to Odoo's mail servers.

SMTP is replaced during tests. While Odoo runs with `--test-enable`, `_smtp_connect` returns a silent client so a real mailbox is never contacted.

Run them with a module update:

```bash
odoo -d odoo14 -u email_inbox --test-enable --stop-after-init --no-http
```

---

# Testes

`test_email_inbox.py` confere envio, respostas POP3, o login `recent:` do Gmail, os presets de provedor, o modelo HTML, a prévia limpa e o vínculo com os servidores de e-mail do Odoo.

O SMTP é trocado durante os testes. Enquanto o Odoo roda com `--test-enable`, `_smtp_connect` devolve um cliente mudo para uma caixa real nunca ser contatada.

Rode com uma atualização do módulo:

```bash
odoo -d odoo14 -u email_inbox --test-enable --stop-after-init --no-http
```
