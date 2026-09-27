# Static files

Browser assets for the request form.

- `src/js/signature.js` draws the signature on a canvas. The canvas is created inside `_render`, because Odoo clears the widget template before that method runs.
- `src/xml/signature.xml` is the QWeb shell. The pad itself is built in JavaScript.
- `src/scss/it_resource.scss` styles the request cards and the dashed signature pad.

`views/assets.xml` loads the script and the stylesheet. After a change, upgrade the module and press Ctrl+F5, or the browser keeps the old bundle.

---

# Arquivos estáticos

Assets do navegador para o formulário do pedido.

- `src/js/signature.js` desenha a assinatura num canvas. O canvas é criado dentro de `_render`, porque o Odoo apaga o template do widget antes desse método.
- `src/xml/signature.xml` é a casca QWeb. A área de desenho em si é montada no JavaScript.
- `src/scss/it_resource.scss` estiliza os cartões do pedido e a área tracejada da assinatura.

`views/assets.xml` carrega o script e a folha de estilo. Depois de uma mudança, atualize o módulo e pressione Ctrl+F5, senão o navegador fica com o pacote antigo.
