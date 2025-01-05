from simulator.utils.file_reading import validator
import ast

@validator(table='users')
def user_id_validator(new_df, dataset):
    for index, row in new_df.iterrows():
        if isinstance(row['payment_methods'], dict):
            new_df['payment_methods'].iloc[index] = str(row['payment_methods'])
            new_df['saved_passengers'].iloc[index] = str(row['saved_passengers'])
            new_df['reservations'].iloc[index] = str(row['reservations'])
    if 'users' not in dataset:
        return new_df, dataset
    users_dataset = dataset['users']
    for index, row in new_df.iterrows():
        if row['user_id'] in users_dataset.values:
            error_message = f"User id {row['user_id']} is already exists in the users data. You should choose different user id."
            raise ValueError(error_message)
    return new_df, dataset

@validator(table='flights')
def flight_id_validator(new_df, dataset):
    for index, row in new_df.iterrows():
        if isinstance(row['dates'], dict):
            new_df['dates'].iloc[index] = str(row['dates'])
    if 'flights' not in dataset:
        return new_df, dataset
    flights_dataset = dataset['flights']
    for index, row in new_df.iterrows():
        if row['flight_number'] in flights_dataset.values:
            error_message = f"Flight number {row['flight_number']} is already exists in the flights data. You should choose different flight number."
            raise ValueError(error_message)
    return new_df, dataset
@validator(table='reservations')
def flight_validator(new_df, dataset):
    # The flights validator, validate that the inserted flight in the reservation is valid. This means that the flight should be exist in the flights database with the correct information.
    if 'flights' not in dataset:
        return new_df, dataset
    flights_dataset = dataset['flights']
    error_message = ""
    for index, row in new_df.iterrows():
        row_flights = ast.literal_eval(row['flights'])
        for flight in row_flights:
            if flight['flight_number'] not in flights_dataset['flight_number'].tolist():
                flights_dataset['formatted_string'] = flights_dataset.apply(
                    lambda
                        row: f"flight number: {row['flight_number']}, origin: {row['origin']}, destination: {row['destination']}",
                    axis=1
                )
                error_message += f"Flight number {flight['flight_number']} is not in the flights data."
                continue
            relevant_flight_row = flights_dataset.loc[flights_dataset['flight_number'] == flight['flight_number']]
            if relevant_flight_row['origin'].values[0] != flight['origin']:
                relevant_flight_row['origin'].values[0] = flight['origin']
            if relevant_flight_row['destination'].values[0] != flight['destination']:
                relevant_flight_row['destination'].values[0] = flight['destination']
            cur_date_dict = ast.literal_eval(relevant_flight_row['dates'].values[0])
            if flight['date'] not in list(cur_date_dict.keys()):
                cur_date_dict[flight['date']] = list(cur_date_dict.values())[-1]
                relevant_flight_row['dates'].values[0] = str(cur_date_dict)
            flights_dataset.loc[flights_dataset['flight_number'] == flight['flight_number'], :] = relevant_flight_row
    if not error_message == "":
        flights_data = '\n'.join(flights_dataset['formatted_string'].to_list())
        error_message += f"\nAvailable flights are: {flights_data}. You must modify the reservation with the correct flight information."
        raise ValueError(error_message)
    return new_df, dataset


@validator(table='reservations')
def user_validator(new_df, dataset):
    # The user validator, validate that the inserted user information in the reservation is valid. If not it updates the user information in the users database.
    if 'users' not in dataset:
        return new_df, dataset
    users_dataset = dataset['users']
    reservation_dataset = dataset['reservations']
    for index, row in new_df.iterrows():
        if row['reservation_id'] in reservation_dataset.values:
            error_message = f"Reservation id {row['reservation_id']} is already exists. You should choose different reservation id."
            raise ValueError(error_message)
        relevant_rows = users_dataset.loc[users_dataset['user_id'] == row['user_id']]
        if relevant_rows.empty:
            raise ValueError(f"User id {row['user_id']} is not in the users data.")
        user_row = relevant_rows.iloc[0]
        payment_history = str(row['payment_history'])
        payment_history = ast.literal_eval(payment_history)
        user_payment_methods = ast.literal_eval(user_row['payment_methods'])
        for payment in payment_history:
            if payment['payment_id'] not in list(user_payment_methods.keys()):
                user_payment_methods[payment['payment_id']] = {'id': payment['payment_id'],
                                                                      'last_four': 1234,
                                                                      'brand': 'visa',
                                                                      'source': 'card'}
        user_row['payment_methods'] = str(user_payment_methods)
        row['passengers'] = str(row['passengers'])
        passengers = ast.literal_eval(row['passengers'])
        user_passengers = ast.literal_eval(user_row['saved_passengers'])
        for passenger in passengers:
            if passenger not in user_passengers:
                user_passengers.append(passenger)
        user_row['saved_passengers'] = str(user_passengers)
        reservations = ast.literal_eval(user_row['reservations'])
        if row['reservation_id'] not in reservations:
            reservations.append(row['reservation_id'])
        user_row['reservations'] = str(reservations)
        users_dataset.loc[users_dataset['user_id'] == row['user_id'], :] = user_row
    return new_df, dataset