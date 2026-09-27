# Signature widget

`signature.js` registers the field widget `it_signature` on the binary signature field.

How to use it on a form: set `widget="it_signature"` on that field and open the dialog in edit mode. A readonly form never receives the pointer events, so the pad looks frozen.

The drawing surface is a canvas of 520 by 160, created in `_render`. A **Clear signature** button wipes it. On pointer up, the image is stored as a PNG data URL. Confirm still requires a drawn image.

---

# Widget de assinatura

`signature.js` registra o widget de campo `it_signature` no campo binário da assinatura.

Como usar num formulário: coloque `widget="it_signature"` nesse campo e abra o diálogo em modo de edição. Um formulário somente leitura não recebe os eventos do ponteiro, então a área parece travada.

A superfície de desenho é um canvas de 520 por 160, criado em `_render`. O botão **Clear signature** limpa. Ao soltar o ponteiro, a imagem é gravada como data URL PNG. Confirmar ainda exige uma imagem desenhada.
