# IT resource inbox

Odoo 14 addons. The branch name is `14.0`.

| Folder | Module | Needs |
| --- | --- | --- |
| `email_inbox` | Email Inbox | Odoo mail and fetchmail |
| `it_resource_request` | IT resource requests | `email_inbox` |

Each folder is one installable module. The repository root is the folder that contains them. Odoo, Doodba and `spec.yaml` all read the modules from that root.

License: LGPL-3.

## Doodba (`repos.yaml` and `addons.yaml`)

`repos.yaml` downloads the branch. `addons.yaml` chooses which modules from that download are linked into Odoo.

```yaml
# odoo/custom/src/repos.yaml
./it-resource-inbox:
  defaults:
    depth: $DEPTH_DEFAULT
  remotes:
    origin: https://github.com/araysolucoes/it-resource-inbox.git
  target: origin 14.0
  merges:
    - origin 14.0
```

On a Doodba 14 image, `origin $ODOO_VERSION` is the same branch, because `$ODOO_VERSION` is `14.0`.

```yaml
# odoo/custom/src/addons.yaml
it-resource-inbox:
  - email_inbox
  - it_resource_request
```

Then aggregate the repositories and restart Odoo. Install **Email Inbox** first. **IT resource requests** depends on it.

## spec.yaml (Akretion docky / git-aggregator)

```yaml
it-resource-inbox:
  modules:
    - email_inbox
    - it_resource_request
  src: https://github.com/araysolucoes/it-resource-inbox.git 14.0
```

Run the usual `ak build` from the folder that contains this file. The modules land under the external source directory, and that directory is what goes on `addons_path`.

## Odoo without Doodba

```bash
git clone --branch 14.0 https://github.com/araysolucoes/it-resource-inbox.git
```

Add the cloned folder (the one that contains `email_inbox` and `it_resource_request`) to `addons_path`. Update the apps list and install **Email Inbox**, then **IT resource requests**.

---

# Caixa e pedidos de TI

Addons para Odoo 14. O nome da branch é `14.0`.

| Pasta | Módulo | Depende de |
| --- | --- | --- |
| `email_inbox` | Caixa de e-mail | mail e fetchmail do Odoo |
| `it_resource_request` | Pedidos de recurso de TI | `email_inbox` |

Cada pasta é um módulo instalável. A raiz do repositório é a pasta que contém os dois. Odoo, Doodba e `spec.yaml` leem os módulos a partir dessa raiz.

Licença: LGPL-3.

## Doodba (`repos.yaml` e `addons.yaml`)

O `repos.yaml` baixa a branch. O `addons.yaml` escolhe quais módulos dessa baixa entram no Odoo.

```yaml
# odoo/custom/src/repos.yaml
./it-resource-inbox:
  defaults:
    depth: $DEPTH_DEFAULT
  remotes:
    origin: https://github.com/araysolucoes/it-resource-inbox.git
  target: origin 14.0
  merges:
    - origin 14.0
```

Numa imagem Doodba 14, `origin $ODOO_VERSION` é a mesma branch, porque `$ODOO_VERSION` vale `14.0`.

```yaml
# odoo/custom/src/addons.yaml
it-resource-inbox:
  - email_inbox
  - it_resource_request
```

Depois agregue os repositórios e reinicie o Odoo. Instale **Email Inbox** primeiro. **IT resource requests** depende dele.

## spec.yaml (Akretion docky / git-aggregator)

```yaml
it-resource-inbox:
  modules:
    - email_inbox
    - it_resource_request
  src: https://github.com/araysolucoes/it-resource-inbox.git 14.0
```

Rode o `ak build` de sempre na pasta desse arquivo. Os módulos caem no diretório de fontes externas, e esse diretório é o que entra no `addons_path`.

## Odoo sem Doodba

```bash
git clone --branch 14.0 https://github.com/araysolucoes/it-resource-inbox.git
```

Coloque a pasta clonada (a que contém `email_inbox` e `it_resource_request`) no `addons_path`. Atualize a lista de aplicativos e instale **Email Inbox**, depois **IT resource requests**.
