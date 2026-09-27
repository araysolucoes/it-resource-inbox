# QWeb

`signature.xml` is the template named for the signature widget. Odoo renders it and then calls `_render`, which replaces the contents with the live canvas.

Keep the template so the widget has a root node. Do not put the only canvas here and expect it to survive `_render`.

---

# QWeb

`signature.xml` é o template do widget de assinatura. O Odoo o renderiza e depois chama `_render`, que substitui o conteúdo pelo canvas vivo.

Mantenha o template para o widget ter um nó raiz. Não coloque o único canvas aqui esperando que ele sobreviva a `_render`.
