from odoo import api, fields, models
from apyori import apriori
import json


class demo(models.Model):
    _name = "pos_recommender.demo"

    @api.model
    def get_customer_order(self, client_id):
        so = self.env['sale.order'].search([('partner_id','=',client_id),('state','=','sent')], limit=1)
        result = []
        if so:
            for item in so.order_line:
                i = 0
                while i<item.product_uom_qty:
                    result.append(item.product_id.id)
                    i=i+1
        # print(result)
        return result

    @api.model
    def my_method(self, items, cusinfo):
        
        return self.get_recommended_items(items, cusinfo)

    # Get recommend items
    # Example return: ['C', 'A', 'D', 'E', 'F']
    def get_recommended_items(self, items, cusinfo):
        # rules = []
        # recommendedItems = []
        # for rule in rules:
        #     if(self.is_included(rule, items)):
        #         if(rule['add'] not in recommendedItems):
        #             recommendedItems.append(rule['add'])
        
        result = []

        products = self.env['product.template'].search([])

        # Get item ids
        item_ids = []
        for item in items:
            for product in products:
                if (product.name == item.strip()):
                    item_ids.append(product.id)
        
        
        #Get customer infomation
        print cusinfo
        customer = self.env['res.partner'].search([('name', '=', cusinfo.strip())])
        
        # Get rules upto customer
        if(customer):
            if(customer.age > 0):
                age_type = 'type1' if customer.age in range(16, 31) else 'type2'
                rule_type = self.env['association.rules.type2'].search([('age_type', '=', age_type), ('gender', '=', customer.gender)])
            else:
                rule_type = self.env['association.rules.type1'].search([])
        else:
            rule_type = self.env['association.rules.type1'].search([])

        # Get rule from rule_type recordset and save to rules list
        # Rule: type dictionary
        rules = []
        for record in rule_type:
            rules.append(json.loads(record.rule))

        # Get recommendedItems from rule and item_ids
        recommendedItems = []        
        for rule in rules:
            if(self.is_included(rule, item_ids)):
                if((rule['add'] not in recommendedItems) and (rule['add'] not in item_ids)):
                    recommendedItems.append(rule['add'])

        
        #Get product recordset from recommendedItems
        recommendedProductRecordset = self.env['product.template'].browse(recommendedItems)

        # Get product info from recordset and save to result list
        for product in recommendedProductRecordset:
            product_product = self.env['product.product'].search([('product_tmpl_id','=',product.id)],limit=1)
            link = '../../web/image?model=product.product&field=image_medium&id=' + str(product_product.id)
            #Save product infomation to product return
            # product_template = self.env['product.template'].search([('id','=',product.product_tmpl_id.id)])
            product_return = {'name':product.name.strip(), 'id':product.id, 'price':product.list_price,'image':link}
            #Add product to result array
            result.append(product_return)
            break
        #######################

        return result

    # Check if item base in rule is included in order items
    def is_included(self, rule, items):
        for item in rule['base']:
            if(item not in items):
                return False
        return True

    # rules = [
    #   {'add': ['D'], 'base': ['A', 'C', 'B'], 'confidence': 0.75}
    #   {'add': ['A', 'S'], 'base': ['D', 'C', 'B'], 'confidence': 0.75},
    # ]
    def format_rules(self, aprioriList):
        rules = []
        for item in aprioriList:
            if(len(item.items) >= 2):
                for rule in item.ordered_statistics:
                    rules.append({'base': list(rule.items_base), 'add': list(rule.items_add), 'confidence': rule.confidence})
        return rules


    

