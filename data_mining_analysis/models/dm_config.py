# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from apyori import apriori
from odoo.exceptions import ValidationError, UserError
import json
import pyfpgrowth

class DMShow(models.Model):
    _name = 'data.mining.show'
    name = fields.Char(string='Name')
    product_base_ids = fields.Many2many(comodel_name='product.product',
                                        relation='data_mining_show_base_rel',
                                        string="Product Base")
    product_add_ids = fields.Many2many(comodel_name='product.product',
                                        relation='data_mining_show_add_rel',
                                        string="Product Add")
    rule_type = fields.Char(string='Rule type')
    # age_type = fields.Char(string='Age Type', required=False)
    # gender = fields.Selection(string='Gender', required=False, selection=[('male', 'Male'), ('female', 'Female'),])

class DMConfig(models.Model):
    _name = 'data.mining.config'
    name = fields.Char(string="Name")
    active = fields.Boolean(default=True,
                            help="If you uncheck the active field, it will disable the record rule without deleting record")
    rule_type = fields.Selection([('apriori', 'Apriori')],
                                     string='Rule Type')
    interval_number = fields.Integer(string="Interval Number", help="Repeat every x")
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('month', 'Months')],
                                     string='Interval Unit')
    min_supp = fields.Float(string='Minium Support', default=1, digits=(32, 6))
    min_conf = fields.Float(string='Minium Confidence', default=1, digits=(32, 6))
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    @api.model
    def create(self, vals):
        if(self.env['data.mining.config'].search_count([]) != 0):
            raise ValidationError(_('Only one record active at the same time'))

        cron_data = {
            'name': vals['name'],
            'interval_number': vals['interval_number'],
            'interval_type': vals['interval_type'],
            'numbercall': -1,
            # 'nextcall': ,
            'model': self._name,
            'args': (vals['min_supp'],vals['min_conf']),
            'function': 'store_association_rules',
            'priority': 6,
            'user_id': self.env.user.id
        }
        cron = self.env['ir.cron'].sudo().create(cron_data)
        return super(DMConfig, self).create(vals)

    @api.multi
    def write(self, vals):
        cron = self.env['ir.cron'].search([('function','=','store_association_rules')],limit=1)
        cron_data = {
            'name': vals.get('name') if vals.get('name') else self.name,
            'interval_number': vals.get('interval_number') if vals.get('interval_number') else self.interval_number,
            'interval_type': vals.get('interval_type') if vals.get('interval_type') else self.interval_type,
            'numbercall': -1,
            # 'nextcall': ,
            'model': self._name,
            'args': (vals.get('min_supp') if vals.get('min_supp') else self.min_supp,
                     vals.get('min_conf') if vals.get('min_conf') else self.min_conf),
            'function': 'store_association_rules',
            'priority': 6,
            'user_id': self.env.user.id
        }
        cron.write(cron_data)
        return super(DMConfig, self).write(vals)

    @api.multi
    def toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            count = self.env['association.rule.config'].search_count([])
            if(not record.active and count!=0):
                raise ValidationError(_('Only one record active at the same time'))
            record.active = not record.active

    @api.model
    def store_association_rules(self, minsupp, minconf):
        return True

    @api.multi
    def run_rule_manually(self):
        for record in self:
            transactions = self.get_sale_data()
            if(record.rule_type == 'apriori' ):
                results = self.format_rules(list(apriori(transactions, min_support=record.min_supp, min_confidence=record.min_conf)))
                self.update_rule(results,'apriori')
            else:
                totalRow = len(transactions)
                print('BEGIN RUN RULE------------------------------')
                results = self.format_rules_fp(pyfpgrowth.generate_association_rules(pyfpgrowth.find_frequent_patterns(transactions, totalRow*record.min_supp),record.min_conf))
                print('AFTER RUN RULE------------------------------')
                self.update_rule(results,'fpgrowth')
            self.update_on_web()
            return {
                'type': 'ir.actions.act_window',
                'name': 'View Rules',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'data.mining.show',
                'target': 'current',
            }

    @api.multi
    def get_sale_data(self):
        result=[]
        sale_list = self.env['sale.order'].search([])
        for sale in sale_list:
            if sale.order_line:
                item = []
                for line in sale.order_line:
                    if line.product_id:
                        item.append(line.product_id.id)
                result.append(item)
        return result

    def format_rules(self, aprioriList):
        rules = []
        for item in aprioriList:
            if(len(item.items) >= 2):
                for rule in item.ordered_statistics:
                    rule_in_json = json.dumps({'base': list(rule.items_base), 'add': list(rule.items_add)})
                    rules.append(rule_in_json)
        return rules

    def update_rule(self,rule_list,algorithm_name):
        self.env['data.mining.show'].search([]).unlink()
        i = 0
        for record in rule_list:
            rule = json.loads(record)
            association = self.env['data.mining.show'].create({
                'product_base_ids': [(6, 0, rule['base'] if isinstance(rule['base'], list) else [rule['base']])],
                'product_add_ids': [(6, 0, rule['add'] if isinstance(rule['add'], list) else [rule['add']])],
                'rule_type': algorithm_name
            })
            i = i + 1
            s = 'RULE no ' + str(i)
            association.write({'name': s})
        return True

    def update_on_web(self):
        self.set_publish_product()
        self.reset_product_recommend()
        rule_list = self.env['data.mining.show'].search([])
        for rule in rule_list:
            if len(rule.product_base_ids)==1:
                product_tmpl = self.env['product.template'].search([('id','=',rule.product_base_ids[0].product_tmpl_id.id)])
                for item in rule.product_add_ids:
                    if item not in product_tmpl.accessory_product_ids:
                        product_tmpl.update({'accessory_product_ids': [(4, item.id)]})

    def set_publish_product(self):
        products = self.env['product.template'].search([('website_published', '=', False)])
        for item in products:
            item.website_published = True

    def reset_product_recommend(self):
        products = self.env['product.template'].search([])
        for product in products:
            product.update({'alternative_product_ids': [(6, 0, [])],
                            'accessory_product_ids': [(6, 0, [])]})
    # nghia
    def format_rules_fp(self, fplist):
        results = []
        for key, item in fplist.iteritems() :
            jsonlist={}
            jsonlist['base']=list(key)
            jsonlist['add']=list(item[0])
            jsonlist['conf']=item[1]
            results.append(jsonlist)
        return results