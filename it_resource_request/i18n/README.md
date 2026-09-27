# Translations

Odoo standard translation folder. The source language of the module is English, so there is no `en_US.po`. English is what the Python, XML, and JavaScript files already say.

| File | Language |
| --- | --- |
| `it_resource_request.pot` | Template of every English source string |
| `pt_BR.po` | Brazilian Portuguese |
| `pt_PT.po` | Portuguese from Portugal |
| `es_ES.po` | Spanish from Spain |

`msgid` is the English text. `msgstr` is the translation. An empty `msgstr` keeps English.

After editing a `.po` file, upgrade the module and press Ctrl+F5. The user must have that language installed and selected on their preferences.

To export a fresh template after new strings are added:

```bash
odoo -d odoo14 --modules=it_resource_request --i18n-export=it_resource_request.pot --language=pot --stop-after-init --no-http
```

---

# Traduções

Pasta padrão de tradução do Odoo. O idioma de origem do módulo é o inglês, então não existe `en_US.po`. Inglês é o que os arquivos Python, XML e JavaScript já dizem.

| Arquivo | Idioma |
| --- | --- |
| `it_resource_request.pot` | Modelo de cada texto de origem em inglês |
| `pt_BR.po` | Português do Brasil |
| `pt_PT.po` | Português de Portugal |
| `es_ES.po` | Espanhol da Espanha |

`msgid` é o texto em inglês. `msgstr` é a tradução. Um `msgstr` vazio mantém o inglês.

Depois de editar um `.po`, atualize o módulo e pressione Ctrl+F5. O usuário precisa ter esse idioma instalado e escolhido nas preferências.

Para exportar um modelo novo depois de incluir textos:

```bash
odoo -d odoo14 --modules=it_resource_request --i18n-export=it_resource_request.pot --language=pot --stop-after-init --no-http
```
