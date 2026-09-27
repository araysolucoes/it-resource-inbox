# Views

Screens for accounts, messages, and templates, plus the menus and the asset bundle.

- `email_account_views.xml` is the account list and form: provider, address, password, SMTP and POP switches, signature banner, and the two Odoo server links.
- `email_message_views.xml` is the kanban and form for Inbox, Other, Sent, Drafts, Failed, and All. Each action has its own domain.
- `email_template_views.xml` is the template list and form used by other modules.
- `menus.xml` builds Email inbox, Messages, Writing, and Settings.
- `assets.xml` loads the stylesheet from `static`.

After a view change, upgrade the module and press Ctrl+F5.

---

# Visões

Telas de contas, mensagens e modelos, mais os menus e o pacote de assets.

- `email_account_views.xml` é a lista e o formulário da conta: provedor, endereço, senha, interruptores de SMTP e POP, banner de assinatura e os dois vínculos com servidores do Odoo.
- `email_message_views.xml` é o kanban e o formulário de Inbox, Other, Sent, Drafts, Failed e All. Cada ação tem o próprio domínio.
- `email_template_views.xml` é a lista e o formulário do modelo usado por outros módulos.
- `menus.xml` monta Email inbox, Messages, Writing e Settings.
- `assets.xml` carrega a folha de estilo de `static`.

Depois de mudar uma visão, atualize o módulo e pressione Ctrl+F5.
