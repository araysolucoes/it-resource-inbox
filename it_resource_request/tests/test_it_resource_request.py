# -*- coding: utf-8 -*-
"""Tests of the IT resource request flow, approvals, demo loader and access levels."""
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

PNG = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8'
    'z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


class FakeSmtp(object):
    def __init__(self):
        self.sent = []

    def send_message(self, mime):
        self.sent.append(mime)

    def quit(self):
        return None


class TestItResourceRequest(TransactionCase):

    def _need(self, name, code, **flags):
        category = self.env['it.resource.need.category'].create({'name': name})
        values = {
            'name': name,
            'code': code,
            'category_id': category.id,
            'description': name,
        }
        values.update(flags)
        return self.env['it.resource.need'].create(values)

    def _sign(self, request, term_type):
        sign = request.signature_ids.filtered(
            lambda item: item.term_type == term_type and item.state == 'pending'
        )[:1]
        sign.signature = PNG
        sign.action_sign()

    def test_fluxo_sem_aprovacao_ate_devolucao(self):
        self._need('Headset', 'headset_need')
        item = self.env['it.resource.item'].create({
            'name': 'Headset',
            'tracking': 'quantity',
            'qty_on_hand': 5,
        })
        pedido = self.env['it.resource.request'].request_for(
            'res.partner', 1, [{'code': 'headset_need', 'quantity': 1}], confirm=True,
        )
        self.assertEqual(pedido.state, 'aprovado')
        pedido.action_start()
        pedido.action_to_allocation()
        pedido.line_ids.item_id = item
        pedido.action_check_availability()
        self.assertEqual(pedido.line_ids.availability, 'ok')
        pedido.action_deliver()
        self.assertEqual(pedido.state, 'entregue')
        self._sign(pedido, 'receipt')
        self.assertEqual(pedido.state, 'em_uso')
        self.assertEqual(item.qty_on_hand, 4)
        pedido.action_start_return()
        self._sign(pedido, 'return')
        self.assertEqual(pedido.state, 'devolvido')
        self.assertEqual(item.qty_on_hand, 5)
        self.assertIn(pedido, self.env['it.resource.request'].for_record('res.partner', 1))

    def test_aprovacao_ti_e_recusa(self):
        aprovador = self.env['res.users'].create({
            'name': 'Aprovador TI',
            'login': 'aprovador_ti_teste',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('it_resource_request.group_it_approval_ti').id,
            ])],
        })
        outro = self.env['res.users'].create({
            'name': 'Fora da lista',
            'login': 'fora_lista_ti_teste',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('it_resource_request.group_it_resource_user').id,
            ])],
        })
        self._need('VPN', 'vpn_need', approve_ti=True)
        pedido = self.env['it.resource.request'].request_for(
            False, 0, [{'code': 'vpn_need'}], confirm=True,
        )
        self.assertEqual(pedido.state, 'aguardando_aprovacao')
        aprovacao = pedido.approval_ids
        with self.assertRaises(UserError):
            aprovacao.with_user(outro)._decide('approved', 'ok')
        aprovacao.with_user(aprovador)._decide('approved', 'Pode ser o acesso padrão.')
        self.assertEqual(pedido.state, 'aprovado')
        self.assertEqual(aprovacao.note, 'Pode ser o acesso padrão.')

        pedido2 = self.env['it.resource.request'].request_for(
            False, 0, [{'code': 'vpn_need'}], confirm=True,
        )
        pedido2.approval_ids.with_user(aprovador)._decide('refused', 'Sem vaga.')
        self.assertEqual(pedido2.state, 'nao_aprovado')

    def test_resposta_de_terceiro_por_email(self):
        account = self.env['email.account'].create({
            'name': 'Terceiros',
            'email': 'ti@example.com',
            'smtp_host': 'smtp.example.com',
            'smtp_enabled': True,
            'pop3_host': 'pop.example.com',
            'pop_enabled': True,
            'is_default': True,
        })
        setting = self.env['it.resource.setting'].get_setting()
        self.env['it.resource.approval.template'].create({
            'setting_id': setting.id,
            'name': 'Aprovar recurso',
            'kind': 'third',
            'email_to': 'fornecedor@example.com',
            'body': 'Responda com a linha {{aprovar}} ou {{recusar}}.',
            'approve_token': 'APROVADO',
            'refuse_token': 'RECUSADO',
            'in_use': True,
        })
        self._need('Licença', 'licenca_need', approve_third=True)
        smtp = FakeSmtp()
        with patch.object(type(account), '_smtp_connect', return_value=smtp):
            pedido = self.env['it.resource.request'].request_for(
                False, 0, [{'code': 'licenca_need'}], confirm=True,
            )
        self.assertEqual(pedido.state, 'aguardando_aprovacao')
        self.assertEqual(len(smtp.sent), 1)
        self.env['email.message'].create({
            'account_id': account.id,
            'direction': 'in',
            'state': 'received',
            'subject': 'Re: pedido',
            'body': 'APROVADO\nLiberar a licença anual.',
            'email_from': 'fornecedor@example.com',
            'email_to': account.email,
            'res_model': 'it.resource.request',
            'res_id': pedido.id,
        })
        pedido.approval_ids._read_one_reply(setting)
        self.assertEqual(pedido.state, 'aprovado')
        self.assertIn('Liberar a licença anual.', pedido.approval_ids.note)

    def test_envio_de_teste_com_dados_simulados(self):
        account = self.env['email.account'].create({
            'name': 'Padrao teste',
            'email': 'ti@example.com',
            'smtp_host': 'smtp.example.com',
            'smtp_enabled': True,
            'pop3_host': 'pop.example.com',
            'pop_enabled': True,
            'is_default': True,
        })
        setting = self.env['it.resource.setting'].get_setting()
        template = self.env['it.resource.approval.template'].create({
            'setting_id': setting.id,
            'name': 'Teste simulado',
            'kind': 'third',
            'email_to': 'fornecedor@example.com',
            'body': 'Pedido {{{pedido}}}: {{{necessidades}}}. Responda {{{aprovar}}}.',
            'approve_token': 'APROVADO',
            'refuse_token': 'RECUSADO',
            'in_use': True,
        })
        smtp = FakeSmtp()
        with patch.object(type(account), '_smtp_connect', return_value=smtp):
            template.action_send_test()
        self.assertEqual(len(smtp.sent), 1)
        self.assertIn('fornecedor@example.com', smtp.sent[0]['To'])
        plain = smtp.sent[0].get_body(preferencelist=('plain',)).get_content()
        self.assertIn('IT/TEST', plain)
        self.assertIn('VPN access, Headset', plain)
        self.assertIn('APROVADO', plain)

    def test_classificacao_da_resposta(self):
        Approval = self.env['it.resource.approval']
        self.assertEqual(
            Approval._classify_reply('APROVADO\nsegue observação', 'APROVADO', 'RECUSADO'),
            'approved',
        )
        self.assertEqual(
            Approval._classify_reply('RECUSADO', 'APROVADO', 'RECUSADO'),
            'refused',
        )
        self.assertFalse(Approval._classify_reply('ainda não sei', 'APROVADO', 'RECUSADO'))

    def test_usuario_comum_nao_aloca(self):
        usuario = self.env['res.users'].create({
            'name': 'Solicitante TI',
            'login': 'solicitante_ti_etapa',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('it_resource_request.group_it_resource_user').id,
            ])],
        })
        self._need('Teclado', 'teclado_need')
        pedido = self.env['it.resource.request'].request_for(
            False, 0, [{'code': 'teclado_need'}], confirm=True,
        )
        pedido.action_start()
        with self.assertRaises(UserError):
            pedido.with_user(usuario).action_to_allocation()

    def test_demo_sem_email_deixa_modelo_de_fora(self):
        setting = self.env['it.resource.setting'].get_setting()
        self.env['it.resource.approval.template'].search([
            '|',
            ('name', '=', 'Demo: third-party approval'),
            ('name', '=', 'Demonstração: aprovação de terceiros'),
        ]).unlink()
        with patch.object(type(setting), '_demo_mail_ready', return_value=False):
            result = setting.action_load_demo()
        self.assertTrue(self.env['it.resource.need'].search([('code', '=', 'demo_vpn')]))
        self.assertFalse(self.env['it.resource.approval.template'].search([
            '|',
            ('name', '=', 'Demo: third-party approval'),
            ('name', '=', 'Demonstração: aprovação de terceiros'),
        ]))
        self.assertIn('email', result['params']['message'])
        with patch.object(type(setting), '_demo_mail_ready', return_value=False):
            again = setting.action_load_demo()
        self.assertEqual(self.env['it.resource.need'].search_count([('code', '=', 'demo_vpn')]), 1)
        self.assertIn('already loaded', again['params']['message'])

    def test_demo_com_email_grava_modelo_sem_enviar(self):
        setting = self.env['it.resource.setting'].get_setting()
        self.env['it.resource.approval.template'].search([
            '|',
            ('name', '=', 'Demo: third-party approval'),
            ('name', '=', 'Demonstração: aprovação de terceiros'),
        ]).unlink()
        before = self.env['email.message'].search_count([])
        with patch.object(type(setting), '_demo_mail_ready', return_value=True):
            result = setting.action_load_demo()
        self.assertTrue(self.env['it.resource.approval.template'].search([
            ('name', '=', 'Demo: third-party approval'),
            ('email_to', '=', 'aprovador.demo@example.com'),
        ]))
        self.assertEqual(self.env['email.message'].search_count([]), before)
        self.assertIn('email templates', result['params']['message'])

    def test_cada_nivel_ve_so_o_seu_recorte(self):
        solicitante = self.env['res.users'].create({
            'name': 'Só as próprias',
            'login': 'so_as_proprias',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('it_resource_request.group_it_resource_user').id,
            ])],
        })
        aprovador = self.env['res.users'].create({
            'name': 'Só a aprovação',
            'login': 'so_a_aprovacao',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('it_resource_request.group_it_approval_ti').id,
            ])],
        })
        gestor = self.env['res.users'].create({
            'name': 'Vê todas',
            'login': 've_todas',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('it_resource_request.group_it_resource_manager').id,
            ])],
        })
        self._need('VPN por nível', 'vpn_nivel', approve_ti=True)
        minha = self.env['it.resource.request'].with_user(solicitante).request_for(
            False, 0, [{'code': 'vpn_nivel'}], confirm=False,
        )
        dos_outros = self.env['it.resource.request'].request_for(
            False, 0, [{'code': 'vpn_nivel'}], requested_by=gestor.id, confirm=True,
        )
        Pedido = self.env['it.resource.request']
        self.assertIn(minha, Pedido.with_user(solicitante).search([]))
        self.assertNotIn(dos_outros, Pedido.with_user(solicitante).search([]))
        self.assertIn(dos_outros, Pedido.with_user(aprovador).search([]))
        self.assertNotIn(minha, Pedido.with_user(aprovador).search([]))
        self.assertEqual(
            Pedido.with_user(gestor).search_count([('id', 'in', (minha.id, dos_outros.id))]),
            2,
        )
        dos_outros.approval_ids.with_user(aprovador)._decide('approved', 'Pode seguir.')
        self.assertNotIn(dos_outros, Pedido.with_user(aprovador).search([]))

    def test_lista_de_acesso_grava_nivel_e_abas(self):
        pessoa = self.env['res.users'].create({
            'name': 'Sem acesso ainda',
            'login': 'sem_acesso_ainda',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        solicitacoes = self.env.ref('it_resource_request.tab_request')
        catalogo = self.env.ref('it_resource_request.tab_catalog')
        acesso = self.env['it.resource.access'].create({
            'user_id': pessoa.id,
            'level': 'own',
            'tab_ids': [(6, 0, [solicitacoes.id])],
        })
        self.assertEqual(acesso.login, 'sem_acesso_ainda')
        self.assertTrue(pessoa.has_group('it_resource_request.group_it_resource_user'))
        self.assertTrue(pessoa.has_group('it_resource_request.group_it_tab_request'))
        self.assertFalse(pessoa.has_group('it_resource_request.group_it_tab_catalog'))
        acesso.write({
            'level': 'directed',
            'tab_ids': [(4, catalogo.id)],
        })
        self.assertTrue(pessoa.has_group('it_resource_request.group_it_level_directed'))
        self.assertFalse(pessoa.has_group('it_resource_request.group_it_resource_user'))
        self.assertTrue(pessoa.has_group('it_resource_request.group_it_tab_catalog'))
        acesso.write({'level': 'all'})
        self.assertTrue(pessoa.has_group('it_resource_request.group_it_resource_manager'))

    def test_etapa_abre_a_lista_seguinte(self):
        self._need('Cadeira', 'cadeira_need')
        pedido = self.env['it.resource.request'].request_for(
            False, 0, [{'code': 'cadeira_need'}], confirm=True,
        )
        self.assertEqual(pedido.state, 'aprovado')
        action = pedido._open_stage()
        self.assertEqual(action['res_id'], pedido.id)
        self.assertEqual(action['name'], 'With IT')
        pedido.action_start()
        self.assertEqual(pedido.state, 'em_andamento')
        self.assertEqual(pedido.stage_label, 'In progress')
        self.assertEqual(pedido._open_stage()['name'], 'With IT')
