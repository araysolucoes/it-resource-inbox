# IT resource requests

People ask for equipment, VPN, licenses, and other IT items. The catalog is inside this module. It does not use Odoo's inventory.

The words on the screen are English. Portuguese (Brazil), Portuguese (Portugal), and Spanish (Spain) come from the `i18n` folder when the user language is one of those.

Mail goes out through the default account of **Email inbox**. Approval templates are not sent by themselves. A template is used only when someone asks for approval on a real request, or when someone clicks **Send test** on that template.

## Install and open

1. Install **Email inbox**, then **IT resource requests**.
2. Refresh the browser with Ctrl+F5.
3. Open **IT resources**.

## Give someone access

1. Open **Settings**, then **Access**. You need the all_perms group or the Settings tab.
2. Add a line.
3. Pick the user. The list shows the name and the login.
4. Set **Access level**:
   - **Only their own requests**: they see requests they opened.
   - **Directed to them**: they see requests where they are the collaborator, or where an approval is still waiting for them.
   - **All**: they see every request.
5. Set **Access group** by tagging the menus they may open: Requests, Catalog, In use, Settings.
6. Leave the line. The module groups are updated. Other groups on that user are left alone.

The admin user is created with level All and every tab.

## Ask for something

1. Open **Requests**, then **Requesting**, and create a request. You need the Requester level (or All) to create one.
2. Add at least one need. Say who receives it and why.
3. Click **Submit request**. The stage becomes Submitted.
4. Click **Request approval**.
   - If no need requires approval, the request becomes Approved and moves to **With IT**.
   - If a need requires Approval 1, Approval 2, or a third party, the stage becomes Waiting for approval and the template in use is emailed.

## Approve

- Approval 1 and Approval 2 decide inside Odoo with **Approve or refuse**.
- A third party receives the email and replies with the approve word or the refuse word alone on one line.
- When every required approval is accepted, the request moves to **With IT**.
- A refusal sets the stage to Not approved.

## Deliver and return

These buttons belong to all_perms.

1. **Start**, then **Allocate items**.
2. Pick the item on each line and **Check availability**.
3. **Deliver for signature**. The collaborator signs the receipt. The item goes to **In use**.
4. Later, **Start return**. The collaborator signs the return. The quantity comes back.

**Requests** at the top of the Requests menu is the master list. It is grouped by stage, so you see where each request stands. The other menus are the same records filtered by stage.

## Demo data

**Settings**, then **Demo data**, loads sample needs, items, units, and two requests. It does not open a form. Clicking again does not duplicate them.

Email templates are loaded only when an outgoing mail server or an Email inbox account already exists. Demo templates are not marked in use, so they do not send mail on their own.

## Groups behind the access screen

- **Requester**: own requests.
- **Approval 1** and **Approval 2**: pending decisions of that kind. These groups are who gets asked to approve. The access screen does not replace them when the level is Directed.
- **Directed to the user**: collaborator or a person who still has to decide.
- **all_perms**: every request, catalog changes, allocation, and settings.
- **Tab Requests**, **Tab Catalog**, **Tab In use**, **Tab Settings**: which menus open.

---

# Pedidos de recursos de TI

As pessoas pedem equipamento, VPN, licença e outros itens de TI. O catálogo fica neste módulo. Ele não usa o estoque do Odoo.

O texto da tela nasce em inglês. Português (Brasil), português (Portugal) e espanhol (Espanha) vêm da pasta `i18n` quando o idioma do usuário é um desses.

O e-mail sai pela conta padrão do **Email inbox**. Modelo de aprovação não se envia sozinho. O modelo entra só quando alguém pede aprovação num pedido de verdade, ou quando alguém clica em **Send test** naquele modelo.

## Instalar e abrir

1. Instale **Email inbox** e depois **IT resource requests**.
2. Atualize o navegador com Ctrl+F5.
3. Abra **IT resources**.

## Dar acesso a alguém

1. Abra **Settings** e depois **Access**. É preciso o grupo all_perms ou a aba Settings.
2. Inclua uma linha.
3. Escolha o usuário. A lista mostra o nome e o login.
4. Defina **Access level**:
   - **Only their own requests**: vê os pedidos que ele mesmo abriu.
   - **Directed to them**: vê pedidos em que é o colaborador, ou em que uma aprovação ainda espera a decisão dele.
   - **All**: vê todos os pedidos.
5. Defina **Access group** marcando os menus que pode abrir: Requests, Catalog, In use, Settings.
6. Saia da linha. Os grupos do módulo são atualizados. Os outros grupos desse usuário permanecem.

O usuário admin nasce com nível All e todas as abas.

## Pedir alguma coisa

1. Abra **Requests**, depois **Requesting**, e crie um pedido. Para criar, é preciso o nível Requester (ou All).
2. Inclua ao menos uma necessidade. Diga quem recebe e por quê.
3. Clique em **Submit request**. A etapa passa a Submitted.
4. Clique em **Request approval**.
   - Se nenhuma necessidade exige aprovação, o pedido fica Approved e vai para **With IT**.
   - Se uma necessidade exige Approval 1, Approval 2 ou um terceiro, a etapa fica Waiting for approval e o modelo em uso é enviado por e-mail.

## Aprovar

- Approval 1 e Approval 2 decidem dentro do Odoo com **Approve or refuse**.
- O terceiro recebe o e-mail e responde com a palavra de aprovar ou a de recusar sozinha numa linha.
- Quando todas as aprovações exigidas são aceitas, o pedido vai para **With IT**.
- Uma recusa deixa a etapa em Not approved.

## Entregar e devolver

Estes botões são do all_perms.

1. **Start** e depois **Allocate items**.
2. Escolha o item de cada linha e **Check availability**.
3. **Deliver for signature**. O colaborador assina o recebimento. O item vai para **In use**.
4. Depois, **Start return**. O colaborador assina a devolução. A quantidade volta.

**Requests**, no topo do menu Requests, é a lista mestre. Ela vem agrupada por etapa, para mostrar em que pé cada pedido está. Os outros menus são os mesmos registros filtrados pela etapa.

## Dados de demonstração

**Settings** e depois **Demo data** carregam necessidades, itens, unidades e dois pedidos de exemplo. Não abre formulário. Clicar de novo não duplica.

Os modelos de e-mail só entram se já existir um servidor de saída ou uma conta no Email inbox. Os modelos de demonstração não ficam em uso, então não enviam e-mail sozinhos.

## Grupos por trás da tela de acesso

- **Requester**: os próprios pedidos.
- **Approval 1** e **Approval 2**: decisões pendentes daquele tipo. São estes grupos que recebem o pedido para aprovar. A tela de acesso não os substitui quando o nível é Directed.
- **Directed to the user**: colaborador ou alguém que ainda precisa decidir.
- **all_perms**: todos os pedidos, mudanças no catálogo, alocação e configuração.
- **Tab Requests**, **Tab Catalog**, **Tab In use**, **Tab Settings**: quais menus abrem.
