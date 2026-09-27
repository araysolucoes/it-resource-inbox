# -*- coding: utf-8 -*-
"""Tests for sending, POP3 fetching, reply threading and templates.

SMTP and POP3 are replaced by in-memory fakes so no network is used and the
exact MIME messages and UIDL listings can be controlled by each test.
"""
from email.message import EmailMessage
from unittest.mock import patch

from odoo.tests import TransactionCase


class FakeSmtp(object):
    def __init__(self):
        self.sent = []

    def send_message(self, mime):
        self.sent.append(mime)

    def quit(self):
        return None


class FakePop(object):
    def __init__(self, lines_by_uidl):
        self._uidls = list(lines_by_uidl.keys())
        self._lines = lines_by_uidl

    def user(self, user):
        return None

    def pass_(self, password):
        return None

    def uidl(self):
        listings = []
        for index, uidl in enumerate(self._uidls, start=1):
            listings.append(b'%d %s' % (index, uidl.encode('utf-8')))
        return b'+OK', listings, 0

    def retr(self, number):
        uidl = self._uidls[number - 1]
        return b'+OK', self._lines[uidl], 0

    def quit(self):
        return None


class TestEmailInbox(TransactionCase):

    def setUp(self):
        super(TestEmailInbox, self).setUp()
        self.account = self.env['email.account'].create({
            'name': 'Suporte',
            'email': 'suporte@example.com',
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_enabled': True,
            'pop3_host': 'pop.example.com',
            'pop3_port': 995,
            'pop_enabled': True,
        })
        self.smtp = FakeSmtp()

    def test_send_for_record_e_resposta_pop3(self):
        with patch.object(type(self.account), '_smtp_connect', return_value=self.smtp):
            sent = self.account.send_for_record(
                'res.partner', 1, 'cliente@example.com', 'Oi', 'corpo',
            )
        self.assertEqual(sent.state, 'sent')
        self.assertEqual(sent.res_model, 'res.partner')
        self.assertEqual(sent.res_id, 1)
        self.assertEqual(len(self.smtp.sent), 1)

        raw = EmailMessage()
        raw['Subject'] = 'Re: Oi'
        raw['From'] = 'cliente@example.com'
        raw['To'] = self.account.email
        raw['Message-ID'] = '<resposta@test>'
        raw['In-Reply-To'] = sent.message_id
        raw.set_content('resposta')
        fake_pop = FakePop({'UID1': raw.as_bytes().splitlines()})
        with patch.object(type(self.account), '_pop_connect', return_value=fake_pop):
            incoming = self.account.fetch_incoming()
        self.assertEqual(incoming.direction, 'in')
        self.assertEqual(incoming.parent_id, sent)
        self.assertEqual(incoming.res_model, 'res.partner')
        self.assertEqual(incoming.res_id, 1)
        self.assertTrue(incoming.in_inbox)

        with patch.object(type(self.account), '_pop_connect', return_value=fake_pop):
            again = self.account.fetch_incoming()
        self.assertFalse(again)

        outro_uidl = FakePop({'UID1-B': raw.as_bytes().splitlines()})
        with patch.object(type(self.account), '_pop_connect', return_value=outro_uidl):
            duplicada = self.account.fetch_incoming()
        self.assertFalse(duplicada)
        self.assertEqual(self.env['email.message'].search_count([
            ('message_id', '=', '<resposta@test>'),
        ]), 1)

    def test_separa_citacao_da_resposta(self):
        text = (
            'testado\r\n\r\n'
            'On Fri, Sep 25, 2026 at 11:30 PM, <a@b.com> wrote:\r\n\r\n'
            '> Teste\r\n'
        )
        answer, quote = self.env['email.message']._split_body(text)
        self.assertEqual(answer, 'testado')
        self.assertIn('wrote:', quote)
        self.assertIn('> Teste', quote)

    def test_gmail_entra_com_prefixo_recent(self):
        self.account.write({
            'pop3_host': 'pop.gmail.com',
            'pop3_user': 'caixa@gmail.com',
        })
        self.assertEqual(self.account._pop_username(), 'recent:caixa@gmail.com')
        self.account.pop3_user = 'recent:caixa@gmail.com'
        self.assertEqual(self.account._pop_username(), 'recent:caixa@gmail.com')

    def test_provedor_preenche_servidor_e_html(self):
        conta = self.env['email.account'].create({
            'provider': 'hostinger',
            'email': 'loja@example.com',
            'smtp_password': 'segredo',
            'smtp_enabled': True,
        })
        self.assertEqual(conta.smtp_host, 'smtp.hostinger.com')
        self.assertEqual(conta.smtp_port, 465)
        self.assertTrue(conta.smtp_ssl)
        self.assertEqual(conta.pop3_host, 'pop.hostinger.com')
        self.assertEqual(conta.pop3_password, 'segredo')
        self.assertEqual(conta.smtp_user, 'loja@example.com')
        self.assertTrue(conta.mail_server_id)
        self.assertEqual(conta.mail_server_id.smtp_host, 'smtp.hostinger.com')
        self.assertEqual(conta.mail_server_id.smtp_encryption, 'ssl')
        self.assertEqual(conta.mail_server_id.smtp_user, 'loja@example.com')
        self.assertFalse(conta.fetchmail_server_id)
        conta.write({'pop_enabled': True})
        self.assertEqual(conta.fetchmail_server_id.server, 'pop.hostinger.com')
        self.assertEqual(conta.fetchmail_server_id.server_type, 'pop')
        self.assertEqual(conta.fetchmail_server_id.state, 'draft')
        self.assertTrue(conta.fetchmail_server_id.is_ssl)
        template = self.env['email.template'].create({
            'name': 'Html',
            'code': 'html_teste',
            'account_id': conta.id,
            'body_format': 'html',
            'subject': 'Oi {{{nome}}}',
            'body': '<p>Olá {{{nome}}}, pedido {{{pedido}}}</p>',
            'email_to': 'a@b.com',
            'variable_ids': [
                (0, 0, {'name': 'nome', 'description': 'Ana'}),
                (0, 0, {'name': 'pedido', 'description': 'TI/1'}),
            ],
        })
        self.assertIn('Ana', template.preview_html)
        self.assertIn('TI/1', template.preview_html)
        self.assertEqual(
            template._render_text(template.subject, template.browse(), {'nome': 'Ana'}),
            'Oi Ana',
        )
        with patch.object(type(conta), '_smtp_connect', return_value=self.smtp):
            sent = template.send(
                'html_teste', False, 0, values={'nome': 'Leo', 'pedido': 'TI/9'},
            )
        self.assertEqual(sent.body_format, 'html')
        self.assertIn('TI/9', sent.body)
        self.assertEqual(sent.subject, 'Oi Leo')

    def test_modelo_por_codigo_e_conversa(self):
        self.account.is_default = True
        partner = self.env['res.partner'].create({'name': 'Ana'})
        self.env['email.template'].create({
            'name': 'Aviso',
            'code': 'aviso_teste',
            'subject': 'Oi {{object.name}}',
            'body': 'Valor {{extra}}',
            'email_to': 'destino@example.com',
        })
        with patch.object(type(self.account), '_smtp_connect', return_value=self.smtp):
            sent = self.env['email.template'].send(
                'aviso_teste', 'res.partner', partner.id, values={'extra': '10'},
            )
        self.assertEqual(sent.state, 'sent')
        self.assertEqual(sent.subject, 'Oi Ana')
        self.assertIn('10', sent.body)
        self.assertEqual(sent.email_to, 'destino@example.com')
        self.assertEqual(sent.res_model, 'res.partner')
        thread = self.env['email.message'].thread_for('res.partner', partner.id)
        self.assertIn(sent, thread)

    def test_guarda_fora_da_caixa_o_que_nao_e_resposta(self):
        promo = EmailMessage()
        promo['Subject'] = 'Instagram'
        promo['From'] = 'news@instagram.com'
        promo['To'] = self.account.email
        promo['Message-ID'] = '<promo@test>'
        promo.set_content('propaganda')
        fake = FakePop({'UID-PROMO': promo.as_bytes().splitlines()})
        with patch.object(type(self.account), '_pop_connect', return_value=fake):
            created = self.account.fetch_incoming()
        self.assertTrue(created)
        self.assertFalse(created.in_inbox)
        self.assertFalse(self.env['email.message'].search([
            ('id', '=', created.id),
            ('in_inbox', '=', True),
        ]))

        self.account.keep_others = False
        noise = EmailMessage()
        noise['Subject'] = 'Alerta'
        noise['From'] = 'no-reply@google.com'
        noise['To'] = self.account.email
        noise['Message-ID'] = '<alerta@test>'
        noise.set_content('alerta')
        fake_noise = FakePop({'UID-ALERTA': noise.as_bytes().splitlines()})
        with patch.object(type(self.account), '_pop_connect', return_value=fake_noise):
            skipped = self.account.fetch_incoming()
        self.assertFalse(skipped)
        self.assertFalse(self.env['email.message'].search([
            ('message_id', '=', '<alerta@test>'),
        ]))

    def test_previa_sem_html(self):
        plain = self.env['email.message']._plain_preview(
            '<!DOCTYPE html><html><head><style>td{color:red}</style></head>'
            '<body><p>Olá <b>Ana</b></p></body></html>'
        )
        self.assertEqual(plain, 'Olá Ana')
        self.assertNotIn('<', plain)

    def test_envia_email_de_teste_e_avisa_a_origem(self):
        partner = self.env['res.partner'].create({'name': 'Cliente teste'})
        with patch.object(type(self.account), '_smtp_connect', return_value=self.smtp):
            self.account.action_send_test()
            sent = self.account.send_for_record(
                'res.partner', partner.id, 'cliente@example.com', 'Pedido', 'corpo',
            )
        self.assertIn(self.account.email, self.smtp.sent[0]['To'])
        teste = self.env['email.message'].search([
            ('account_id', '=', self.account.id),
            ('subject', '=', 'Sending test'),
        ])
        self.assertEqual(teste.body_format, 'html')
        self.assertEqual(teste.state, 'sent')

        raw = EmailMessage()
        raw['Subject'] = 'Re: Pedido'
        raw['From'] = 'cliente@example.com'
        raw['To'] = self.account.email
        raw['Message-ID'] = '<resp-pedido@test>'
        raw['In-Reply-To'] = sent.message_id
        raw.set_content('aprovado')
        fake = FakePop({'UID-RESP': raw.as_bytes().splitlines()})
        with patch.object(type(self.account), '_pop_connect', return_value=fake):
            incoming = self.account.fetch_incoming()
        self.assertEqual(incoming.parent_id, sent)
        self.assertTrue(incoming.in_inbox)
        if hasattr(partner, 'message_ids'):
            self.assertTrue(any(
                'A reply arrived' in (note.body or '')
                for note in partner.message_ids
            ))
