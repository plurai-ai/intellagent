from simulator.utils.file_reading import validator
import ast
import pandas as pd
import copy


@validator(table='users')
def user_id_validator(new_df, dataset):
    if 'users' not in dataset:
        return new_df, dataset
    users_dataset = dataset['users']
    for index, row in new_df.iterrows():
        if row['user_id'] in users_dataset.values:
            error_message = f"User id {row['user_id']} is already exists in the users data. You should choose different user id."
            raise ValueError(error_message)
    return new_df, dataset

@validator(table='products')
def product_id_validator(new_df, dataset):
    new_df['product_id'] = new_df['product_id'].astype(str)
    if 'products' not in dataset:
        return new_df, dataset
    products_dataset = dataset['products']
    for index, row in new_df.iterrows():
        if row['product_id'] in products_dataset.values:
            error_message = f"Product id {row['product_id']} is already exists in the products data. You should choose different product id."
            raise ValueError(error_message)
    return new_df, dataset

@validator(table='orders')
def order_validator(new_df, dataset):
    for index, row in new_df.iterrows():
        if not row['order_id'].startswith("#"):
            raise ValueError("There must be a '#' symbol at the beginning of the order id.")
    if 'orders' not in dataset:
        return new_df, dataset
    orders_dataset = dataset['orders']
    for index, row in new_df.iterrows():
        if row['order_id'] in orders_dataset.values:
            error_message = f"Order id {row['order_id']} is already exists in the orders data. You should choose different order id."
            raise ValueError(error_message)
    return new_df, dataset

@validator(table='orders')
def order_user_alignment_validator(new_df, dataset):
    users_dataset = dataset['users']
    for index, row in new_df.iterrows():
        relevant_rows = users_dataset.loc[users_dataset['user_id'] == row['user_id']]
        if relevant_rows.empty:
            raise ValueError(f"User id {row['user_id']} is not in the users data. The valid users are: {list(users_dataset['user_id'])}")
        user_row = relevant_rows.iloc[0]
        payment_history = ast.literal_eval(row['payment_history'])
        user_payment_methods = ast.literal_eval(user_row['payment_methods'])
        for payment in payment_history:
            if payment['payment_method_id'] not in list(user_payment_methods.keys()):
                user_payment_methods[payment['payment_method_id']] = {'id': payment['payment_method_id'],
                                                                      'last_four': 1234,
                                                                      'brand': 'visa',
                                                                      'source': 'card',
                                                                      'balance': 50}
        user_row['payment_methods'] = str(user_payment_methods)
        user_orders_list = ast.literal_eval(user_row['orders'])
        if row['order_id'] not in user_orders_list:
            user_orders_list.append(row['order_id'])
        user_row['orders'] = str(user_orders_list)
        users_dataset.loc[users_dataset['user_id'] == row['user_id'], :] = user_row.values
    return new_df, dataset


@validator(table='orders')
def order_products_alignment_validator(new_df, dataset):
    if 'products' not in dataset:
        dataset['products'] = pd.DataFrame()
    products_dataset = dataset['products']
    product_id_list = list(products_dataset['product_id']) if 'product_id' in products_dataset else []
    for index, row in new_df.iterrows():
        update_item_list = False
        if isinstance(row['items'], dict):
            update_item_list = True
            items_list = row['items']
        else:
            items_list = ast.literal_eval(row['items'])
        for item in items_list:
            if str(item['product_id']) not in product_id_list:
                if 'color' not in item['options']:
                    update_item_list = True
                    item['options']['color'] = 'blue'
                item_copy = copy.deepcopy(item)
                hard_coded_variants = {'1011121319': {'item_id': item['item_id'], 'options': item['options'],
                                                      'available': True, 'price': item['price']},
                                       '1011121314': {'item_id': item_copy['item_id'], 'options': item_copy['options'],
                                                      'available': True, 'price': item_copy['price']}}
                cur_prod_color = hard_coded_variants['1011121319']['options']['color']
                if cur_prod_color == 'green':
                    hard_coded_variants['1011121314']['options']['color'] = 'blue'
                else:
                    hard_coded_variants['1011121314']['options']['color'] = 'green'

                new_row = {'name': item['name'], 'product_id': str(item['product_id']),
                           'variants': hard_coded_variants}
                dataset['products'] = pd.concat([dataset['products'], pd.DataFrame([new_row])], ignore_index=True)
            else:
                if 'name' not in item.keys():
                    update_item_list = True
                    item['name'] = products_dataset.loc[products_dataset['product_id'] ==
                                                        str(item['product_id']), 'name'].iloc[0]
                else:
                    products_dataset.loc[products_dataset['product_id'] ==
                                         str(item['product_id']), 'name'] = item['name']
        if update_item_list:
            row['items'] = str(items_list)
    return new_df, dataset