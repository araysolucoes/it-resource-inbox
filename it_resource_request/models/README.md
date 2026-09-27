# Models

The records of an IT request.

- `it_resource_need.py` is what someone asks for (VPN, notebook, license) and which approval that need requires.
- `it_resource_item.py` and `it_resource_unit.py` are the catalog item and, when tracking is by unit, each serial.
- `it_resource_request.py` is the request, its stage, and the buttons that move it. `request_for` is the call other modules use.
- `it_resource_request_line.py` is one need on that request, the chosen item, and the availability.
- `it_resource_approval.py` is one decision: Approval 1, Approval 2, or a third party. Third-party replies are classified by the template words.
- `it_resource_approval_template.py` is the text or HTML that is emailed when a template is in use.
- `it_resource_setting.py` holds the template list and the demo loader.
- `it_resource_term.py` and the signature records are the receipt and return texts people sign.
- `it_resource_assignment.py` is who currently holds a unit.
- `it_resource_access.py` is the access screen: user, login, access level, and menu tabs.

Stage keys such as `solicitando` and `em_andamento` stay stable in the database. Only the label is translated.

---

# Modelos

Os registros de um pedido de TI.

- `it_resource_need.py` é o que alguém pede (VPN, notebook, licença) e qual aprovação essa necessidade exige.
- `it_resource_item.py` e `it_resource_unit.py` são o item do catálogo e, quando o controle é por unidade, cada série.
- `it_resource_request.py` é o pedido, a etapa e os botões que o movem. `request_for` é a chamada que outros módulos usam.
- `it_resource_request_line.py` é uma necessidade nesse pedido, o item escolhido e a disponibilidade.
- `it_resource_approval.py` é uma decisão: Approval 1, Approval 2 ou um terceiro. A resposta do terceiro é classificada pelas palavras do modelo.
- `it_resource_approval_template.py` é o texto ou HTML enviado quando um modelo está em uso.
- `it_resource_setting.py` guarda a lista de modelos e o carregador de demonstração.
- `it_resource_term.py` e os registros de assinatura são os textos de recebimento e devolução que as pessoas assinam.
- `it_resource_assignment.py` é quem está com uma unidade agora.
- `it_resource_access.py` é a tela de acesso: usuário, login, nível de acesso e abas do menu.

As chaves de etapa, como `solicitando` e `em_andamento`, permanecem estáveis no banco. Só o rótulo é traduzido.
