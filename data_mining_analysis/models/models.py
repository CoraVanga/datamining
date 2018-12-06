# -*- coding: utf-8 -*-
# Copyright 2018 IS-LAB
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, models, fields, _
from apyori import apriori
from odoo.exceptions import ValidationError
import json

class AssociationRuleScheduler(models.Model):
    _name = 'association.scheduler'
    _description = 'Association rules mining'

    @api.model
    def store_association_rules_view(self):
        self.env['association.rule.show'].search([]).unlink()
        rule_type_1 = self.env['association.rules.type1'].search([])
        rule_type_2 = self.env['association.rules.type2'].search([])
        i=0
        for record in rule_type_1:
            rule = json.loads(record.rule)
            association = self.env['association.rule.show'].create({
                'product_base_ids':[(6,0,rule['base'] if isinstance(rule['base'],list) else [rule['base']])],
                'product_add_ids': [(6,0,rule['add'] if isinstance(rule['add'],list) else [rule['add']])],
                'rule_type': 'Normal customer'
            })
            i = i +1
            s = 'rule no ' + str(i)
            association.write({'name': s})

        for record in rule_type_2:
            rule = json.loads(record.rule)
            association = self.env['association.rule.show'].create({
                'product_base_ids': [(6, 0, rule['base'] if isinstance(rule['base'], list) else [rule['base']])],
                'product_add_ids': [(6, 0, rule['add'] if isinstance(rule['add'], list) else [rule['add']])],
                'rule_type': 'Valuable customer',
                'age_type': '16-30' if record.age_type == 'type1' else '>30',
                'gender': record.gender
            })
            i = i + 1
            s = 'Rule no ' + str(i)
            association.write({'name': s})

    @api.model
    def store_association_rules(self):
        # Rule model
        rule1_model = self.env['association.rules.type1']
        rule2_model = self.env['association.rules.type2']

        # Remove old rules
        rule1_model.search([]).unlink()                
        rule2_model.search([]).unlink()   

        rule_types = []
        # rule_types have rules [[rules1], [rules2], [rules3], [rules4], ...]
        # Example rules:
        # rules = [
        #   {'rule': '{json_rule1}', 'age': 'type1', 'gender': 'male' },
        #   {'rule': '{json_rule2}', 'age': 'type1', 'gender': 'female' },
        #   {'rule': '{json_rule3}', 'age': 'type2', 'gender': 'male' }
        # ]

        # age_type1 = [16, 30]
        # age_type2 = [31, 70]
            
        rule_types.append(self.mine_rules('type1', "male"))
        rule_types.append(self.mine_rules('type1', "female"))
        rule_types.append(self.mine_rules('type2', "male"))
        rule_types.append(self.mine_rules('type2', "female"))

        for rules in rule_types:
            for rule in rules:    
                rule2_model.create(rule)

        normal_rules = self.mine_rules()

        for rule in normal_rules:
            rule1_model.create(rule)
        
        return "Done"

    def mine_rules(self, age_type="", gender=""):
        if not (age_type and gender):
            customer_ids = self.env['res.partner'].search([]).ids
        else:
            age = []
            if (age_type == 'type1'):
                age = range(16, 31)
            elif (age == 'type2'):
                age = range(31, 71)            

            # Customer ids:
            # Gender: male or female, age: a range
            customer_ids = self.env['res.partner'].search([('gender', '=', gender), ('age', 'in', age)]).ids
        
        # pos_orders:
        pos_orders = self.env['pos.order'].search([('partner_id', 'in', customer_ids)])

        # Get transactions from pos_orders
        transactions = []      
        for order in pos_orders:
            transaction = []
            for line in order.lines:
                transaction.append(line.product_id.id)
            if transaction:
                transactions.append(transaction)

        # Mine rules
        aprioriList = list(apriori(transactions))

        formated_rules =  self.format_rules(aprioriList, age_type, gender)
        return formated_rules

    def format_rules(self, aprioriList, age_type="", gender=""):
        rules = []
        for item in aprioriList:
            if(len(item.items) >= 2):
                for rule in item.ordered_statistics:
                    rule_in_json = json.dumps({'base': list(rule.items_base), 'add': list(rule.items_add)[0]})
                    if (age_type and gender):
                        rules.append({'rule': rule_in_json, 'age_type': age_type, 'gender': gender })
                    else:
                        rules.append({'rule': rule_in_json})                        
        return rules

class AssociationRule1(models.Model):
    _name = 'association.rules.type1'
    _description = 'Association rules basic'
    rule = fields.Text(string='Rule', required=False)

class AssociationRule2(models.Model):
    _name = 'association.rules.type2'
    _description = 'Association rules with age and gender'
    rule = fields.Text(string='Rule', required=False)
    age_type = fields.Char(string='Age Type', required=False)
    gender = fields.Selection(string='gender', required=False, selection=[('male', 'Male'), ('female', 'Female'), ])

class AssociationRuleShow(models.Model):
    _name = 'association.rule.show'
    name = fields.Char(string='Name')
    product_base_ids = fields.Many2many(comodel_name='product.template',
                                        relation='association_rule_show_base_rel',
                                        string="Product Base")
    product_add_ids = fields.Many2many(comodel_name='product.template',
                                        relation='association_rule_show_add_rel',
                                        string="Product Add")
    rule_type = fields.Char(string='Rule type')
    age_type = fields.Char(string='Age Type', required=False)
    gender = fields.Selection(string='Gender', required=False, selection=[('male', 'Male'), ('female', 'Female'), ])

class AssociationRuleConfig(models.Model):
    _name = 'association.rule.config'
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
        if(self.env['association.rule.config'].search_count([]) != 0):
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
        return super(AssociationRuleConfig, self).create(vals)

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
        print(self.name)
        print(cron)
        print(cron_data)
        cron.write(cron_data)
        return super(AssociationRuleConfig, self).write(vals)

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

        rule_type_1 = self.env['association.rules.type1'].search([])
        rule_type_2 = self.env['association.rules.type2'].search([])

        print('Run Function')
        not_del_pro = []
        for record in rule_type_1:
            rule = json.loads(record.rule)
            if (len(rule['base'])==1):
                product = self.env['product.template'].search([('id','=',rule['base'][0])])
                if(product.id not in not_del_pro):
                    product.update({'alternative_product_ids':[(6,0,[])],
                                    'accessory_product_ids':[(6,0,[])]})
                    not_del_pro.append(product.id)
                    print (product.name + 'add')
                else:
                    print (product.name + 'do not add')
                product_product = []
                product_temp = []
                if (isinstance(rule['add'], list)):
                    for item in rule['add']:
                        pp = self.env['product.product'].search([('product_tmpl_id','=',item)], limit=1)
                        print(pp.name)
                        product_product.append(pp.id)
                        product_temp.append(item)
                else:
                    pp = self.env['product.product'].search([('product_tmpl_id', '=', rule['add'])], limit=1)
                    product_product.append(pp.id)
                    product_temp.append(rule['add'])
                product.update({
                    'alternative_product_ids':[
                        (4, item) for item in product_temp],
                    'accessory_product_ids': [
                        (4, item) for item in product_product]})


        # for record in rule_type_2:
        #     rule = json.loads(record.rule)
        #     if (len(rule['base'])==1):
        #         product = self.env['product.template'].search([('id', '=', rule['base'][0])])
        #         product.write({'accessory_product_ids': [
        #             (6, 0, rule['add'] if isinstance(rule['add'], list) else [rule['add']])]})
        return True
    
    
    
