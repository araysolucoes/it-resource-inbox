# Wizard

The compose window.

- `email_compose.py` is the transient form: account, recipients, subject, body, format, and attachments.
- `email_compose_views.xml` is that form, opened as a dialog from **Send message**.

Sending creates an `email.message` and delivers it through the account SMTP. It does not use `mail.mail`.

---

# Assistente

A janela de escrever a mensagem.

- `email_compose.py` é o formulário transitório: conta, destinatários, assunto, corpo, formato e anexos.
- `email_compose_views.xml` é esse formulário, aberto como diálogo a partir de **Send message**.

Enviar cria um `email.message` e entrega pelo SMTP da conta. Não usa `mail.mail`.
