# Wizards

Dialogs that do not keep their own business data.

- `it_resource_approval_template.py` and its view create one approval template: kind, text or HTML, and, for a third party, the destination email plus the approve and refuse words.
- `it_resource_approval_decide.py` and its view are the Approve or refuse dialog. The note is required when refusing. Applying the decision returns the request on the list of its new stage.

Open **New template** from the approval template screen. Open **Approve or refuse** from a request that is waiting for approval.

---

# Assistentes

Diálogos que não guardam dados de negócio próprios.

- `it_resource_approval_template.py` e a visão dele criam um modelo de aprovação: tipo, texto ou HTML e, para terceiro, o e-mail de destino mais as palavras de aprovar e recusar.
- `it_resource_approval_decide.py` e a visão dele são o diálogo Approve or refuse. A observação é obrigatória na recusa. Aplicar a decisão devolve o pedido na lista da etapa nova.

Abra **New template** na tela de modelos de aprovação. Abra **Approve or refuse** num pedido que está aguardando aprovação.
