# Security

Groups and who sees which request.

`it_resource_security.xml` defines the groups and the record rules.

- Requester: `requested_by` is the current user.
- Approval 1: the request still waits for that user.
- Approval 2: the same, for the second approval.
- Directed to the user: the user is the collaborator or still has to decide.
- all_perms: every request. This rule wins because record rules are combined with OR.

`ir.model.access.csv` says which group can read or write each model. The Settings tab can edit the access list. The Requests tab can open requests. Creating a request still requires the Requester or all_perms access rights.

---

# Segurança

Grupos e quem vê qual pedido.

`it_resource_security.xml` define os grupos e as regras de registro.

- Requester: `requested_by` é o usuário atual.
- Approval 1: o pedido ainda espera esse usuário.
- Approval 2: o mesmo, para a segunda aprovação.
- Directed to the user: o usuário é o colaborador ou ainda precisa decidir.
- all_perms: todos os pedidos. Esta regra vence porque as regras de registro se somam com OU.

`ir.model.access.csv` diz qual grupo pode ler ou gravar cada modelo. A aba Settings edita a lista de acessos. A aba Requests abre pedidos. Criar um pedido ainda exige o direito do Requester ou do all_perms.
