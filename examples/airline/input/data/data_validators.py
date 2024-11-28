from simulator.utils.file_reading import validator


@validator(table='reservations')
def flight_validator(new_df, dataset):
    # The flights validator, validate that the inserted flight in the reservation is valid. This means that the flight should be exist in the flights database with the correct information.
    if 'flights' not in dataset:
        return new_df, dataset
    flights_dataset = dataset['flights']
    error_message = ""
    for index, row in new_df.iterrows():
        for flight in row['flights']:
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
            if flight['date'] not in list(dataset['flights'].iloc[0]['dates'].keys()):
                flight['date'] = list(dataset['flights'].iloc[0]['dates'].keys())[0]
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
    for index, row in new_df.iterrows():
        relevant_rows = users_dataset.loc[users_dataset['user_id'] == row['user_id']]
        if relevant_rows.empty:
            raise ValueError(f"User id {row['user_id']} is not in the users data.")
        user_row = relevant_rows.iloc[0]
        for payment in row['payment_history']:
            if payment['payment_id'] not in list(user_row['payment_methods'].keys()):
                user_row['payment_methods'][payment['payment_id']] = {'id': payment['payment_id'],
                                                                      'last_four': 1234,
                                                                      'brand': 'visa',
                                                                      'source': 'card'}
        for passenger in row['passengers']:
            if passenger not in user_row['saved_passengers']:
                user_row['saved_passengers'].append(passenger)
        if row['reservation_id'] not in user_row['reservations']:
            user_row['reservations'].append(row['reservation_id'])
    return new_df, dataset