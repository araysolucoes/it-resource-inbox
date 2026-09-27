# Email inbox

This module is the mailbox other Odoo modules use to send and receive mail. It does not replace Discuss. It keeps its own accounts, templates, and message history.

The words on the screen are English. Portuguese (Brazil), Portuguese (Portugal), and Spanish (Spain) come from the `i18n` folder when the user language is one of those.

## What you can do

- Register a mailbox by picking the provider, the address, and the password. The server, port, and encryption are filled in for you.
- Send plain text or HTML, with an optional signature banner at the bottom.
- Download POP3 mail. Replies to mail this system sent stay in the Inbox. Other mail can sit in Other, or be skipped.
- Let another module send with `send_for_record` or `email.template.send` and read the thread with `thread_for`.
- Mirror the same SMTP and POP3 data into Odoo's own outgoing and incoming server lists. The incoming server stays unconfirmed so this module remains the one that downloads mail.

## Open the app

1. Install **Email inbox**.
2. Refresh the browser with Ctrl+F5.
3. Open **Email inbox** in the main menu.

## Register the first account

1. Go to **Configuration** and open **Email Accounts**. You need the Email Inbox / Manager group.
2. Click **Create**.
3. Choose the provider: Gmail, Outlook, Hostinger, or Localweb.
4. Type the email address and the password. For Gmail, use an app password, not the normal account password.
5. Turn on **Enable SMTP** to send and **Enable POP** to download.
6. Optional: upload a png, jpg, or webp banner. It is added at the end of every outgoing message.
7. Mark **Default account** on the mailbox other modules should use when they do not name one. Only one account stays marked.
8. Save.
9. Click **Test login**, then **Send test email**, then **Test incoming**.

The same account also appears under Odoo Settings, **Outgoing Mail Servers** (active) and **Incoming Mail Servers** (filled in, status Not confirmed).

## Send a message

1. Open **Messages** and click **Send Message**.
2. Pick the account, the recipient, the subject, and the body.
3. Choose text or HTML.
4. Send. A copy is stored under **Sent**.

## Read mail

1. **Inbox** lists replies to messages this system sent.
2. **Others** lists mail that is not a reply, when **Keep the Rest** is on.
3. **Drafts** and **Failed** are outgoing messages that were not sent or were refused.
4. **All** is the full history of that account.

A scheduled action named **Email: fetch POP3** downloads mail every five minutes for every account that has POP enabled.

## Templates for other modules

1. Open **Writing** and then **Templates**. Manager only.
2. Create a template with a stable code, a subject, a body, and optional variables such as `{{{name}}}`.
3. Another module calls `email.template.send` with that code, or `account.send_for_record` when it already has the account.

Triple braces `{{{variable}}}` are replaced before double braces `{{key}}`, so a resource request can still use `{{request}}`, `{{approve}}`, and `{{refuse}}`.

## Groups

- **Email Inbox / User** can read accounts and work with messages.
- **Email Inbox / Manager** can create accounts, templates, and run the test buttons. The admin user is in this group.

---

# Caixa de e-mail

Este módulo é a caixa que os outros módulos do Odoo usam para enviar e receber e-mail. Ele não substitui o Discuss. Ele guarda as próprias contas, os modelos e o histórico.

O texto da tela nasce em inglês. Português (Brasil), português (Portugal) e espanhol (Espanha) vêm da pasta `i18n` quando o idioma do usuário é um desses.

## O que dá para fazer

- Cadastrar uma caixa escolhendo o provedor, o endereço e a senha. Servidor, porta e criptografia são preenchidos sozinhos.
- Enviar texto puro ou HTML, com um banner de assinatura opcional no fim.
- Baixar o POP3. Respostas a um e-mail que o sistema enviou ficam na Caixa de entrada. O resto pode ir para Outros ou ser ignorado.
- Outro módulo envia com `send_for_record` ou `email.template.send` e lê o fio com `thread_for`.
- Os mesmos dados de SMTP e POP3 entram nas listas de servidor de saída e de entrada do próprio Odoo. A entrada fica sem confirmar para este módulo continuar sendo quem baixa as mensagens.

## Abrir o aplicativo

1. Instale **Email inbox**.
2. Atualize o navegador com Ctrl+F5.
3. Abra **Email inbox** no menu principal.

## Cadastrar a primeira conta

1. Vá em **Settings** e abra **Email accounts**. É preciso o grupo Email inbox / Manager.
2. Clique em **Create**.
3. Escolha o provedor: Gmail, Outlook, Hostinger ou Localweb.
4. Informe o e-mail e a senha. No Gmail, use uma senha de app, não a senha normal da conta.
5. Ligue **Enable SMTP** para enviar e **Enable POP** para baixar.
6. Opcional: envie um banner png, jpg ou webp. Ele entra no fim de cada mensagem enviada.
7. Marque **Default account** na caixa que os outros módulos devem usar quando não indicam uma. Só uma conta fica marcada.
8. Salve.
9. Clique em **Test login**, depois **Send test email** e **Test incoming**.

A mesma conta também aparece em Definições do Odoo, **Outgoing Mail Servers** (ativa) e **Incoming Mail Servers** (preenchida, situação Not confirmed).

## Enviar uma mensagem

1. Abra **Messages** e clique em **Send message**.
2. Escolha a conta, o destinatário, o assunto e o texto.
3. Escolha texto ou HTML.
4. Envie. Uma cópia fica em **Sent**.

## Ler o correio

1. **Inbox** lista respostas a mensagens que este sistema enviou.
2. **Other** lista o que não é resposta, quando **Keep the rest** está ligado.
3. **Drafts** e **Failed** são saídas que não foram enviadas ou que o servidor recusou.
4. **All** é o histórico completo daquela conta.

A ação agendada **Email: fetch POP3** baixa a caixa a cada cinco minutos, em toda conta com POP ligado.

## Modelos para outros módulos

1. Abra **Writing** e depois **Templates**. Só o gestor.
2. Crie um modelo com um código estável, assunto, corpo e variáveis opcionais como `{{{name}}}`.
3. Outro módulo chama `email.template.send` com esse código, ou `account.send_for_record` quando já tem a conta.

As chaves triplas `{{{variable}}}` são trocadas antes das duplas `{{key}}`, para um pedido de recurso ainda poder usar `{{request}}`, `{{approve}}` e `{{refuse}}`.

## Grupos

- **Email inbox / User** lê contas e trabalha com mensagens.
- **Email inbox / Manager** cria contas e modelos e usa os botões de teste. O usuário admin está neste grupo.
