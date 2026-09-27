# Security

Who can open the mailbox.

- `email_inbox_security.xml` defines **Email inbox / User** and **Email inbox / Manager**. Manager implies User. The admin user is a manager.
- `ir.model.access.csv` is the read, write, create, and delete grid. Users can work with messages. Only managers can create accounts and templates.

There is no record rule that hides one account from another user. Access is by group, not by ownership of the mailbox.

---

# Segurança

Quem pode abrir a caixa.

- `email_inbox_security.xml` define **Email inbox / User** e **Email inbox / Manager**. Manager implica User. O usuário admin é gestor.
- `ir.model.access.csv` é a grade de ler, gravar, criar e apagar. Usuários trabalham com mensagens. Só gestores criam contas e modelos.

Não há regra de registro que esconda uma conta de outro usuário. O acesso é por grupo, não por dono da caixa.
