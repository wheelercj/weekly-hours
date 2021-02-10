import os
import yaml
import PySimpleGUI as sg


class activity:
    def __init__(self, hpd, dpw, parent):
        self.hpd = hpd        # Hours per day.
        self.dpw = dpw        # Days per week.
        self.parent = parent  # The parent activity.


def main():
    activities = dict()
    if os.path.exists('saved_hours.yaml'):
        activities = load_hours()

    window = create_window(activities)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'save_and_close':
            save_hours(activities)
            window.close()
            return
        elif event == 'cancel':
            choice = sg.popup_ok_cancel('Are you sure you want to lose any unsaved changes?',
                                        title='Confirm')
            if choice == 'OK':
                window.close()
                return

        respond_to_event(event, values, window, activities)


def load_hours():
    with open('saved_hours.yaml', 'r') as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
        activities = dict(data)
        return activities


def save_hours(activities):
    with open('saved_hours.yaml', 'w') as file:
        data = list(activities.items())
        yaml.dump(data, file)


def create_window(activities):
    available_hours = get_available_hours(activities)
    tree_data = get_tree_data(activities)

    layout = [[sg.Tree(tree_data,
                       key='-data-',
                       headings=['hours per day',
                                 'days per week',
                                 'hours per week'],
                       show_expanded=True,
                       auto_size_columns=True,
                       num_rows=25)],
              [sg.Text('Available weekly hours: '),
               sg.Text(available_hours, key='-available-')],
              [sg.Button('new', key='-new-'),
               sg.Button('edit', key='-edit-'),
               sg.Button('delete', key='-delete-')],
              [sg.HorizontalSeparator(pad=(0, 8))],
              [sg.Button('save and close', key='save_and_close'),
               sg.Button('cancel', key='cancel')]]

    return sg.Window('Weekly hours', layout)


def respond_to_event(event, values, window, activities):
    if event == '-new-':
        read_new_activity(values, window, activities)
    elif event == '-edit-':
        edit_activity(values, window, activities)
    elif event == '-delete-':
        delete_activity(values, window, activities)

    try:
        tree_data = get_tree_data(activities)
    except KeyError:
        sg.Popup('Could not find the parent activity', title='Error')

    window['-data-'].update(tree_data)
    window['-available-'].update(get_available_hours(activities))


def read_new_activity(values, window, activities):
    new_window = create_edit_window('', activities)
    show_edit_menu('', activities, new_window)


def Float(entry):
    if entry == '':
        return 0
    else:
        return float(entry)


def create_edit_window(chosen_key, activities):
    if chosen_key != '':
        a = activities[chosen_key]
    else:
        a = activity(None, None, '')

    layout = [[sg.Text('activity name '), sg.Input(key='-name-', default_text=chosen_key)]]
    if not is_parent_activity(chosen_key, activities):
        layout += [[sg.Text('hours per day '), sg.Input(key='-hpd-', default_text=a.hpd)],
                   [sg.Text('days per week'), sg.Input(key='-dpw-', default_text=a.dpw)],
                   [sg.Text('parent activity'), sg.Input(key='-parent-', default_text=a.parent)]]
    layout += [[sg.Button('ok'), sg.Button('cancel')]]

    return sg.Window('edit activity', layout)


def edit_activity(values, window, activities):
    if len(values['-data-']) == 0:
        sg.Popup('Select an activity to edit.', title='Error')
    else:
        chosen_key = values['-data-'][0]
        new_window = create_edit_window(chosen_key, activities)
        show_edit_menu(chosen_key, activities, new_window)


def show_edit_menu(chosen_key, activities, window):
    while True:
        event, new_values = window.read()

        if event == sg.WIN_CLOSED or event == 'cancel':
            window.close()
            return

        if event == 'ok':
            # Rename the values entered for easier use.
            hpd = Float(new_values['-hpd-'])
            dpw = Float(new_values['-dpw-'])
            new_activity = activity(hpd, dpw, new_values['-parent-'])

            # Change the parent activity's data, if necessary.
            # Any parent hpd and dpw is deleted.
            try:
                parent = new_activity.parent
                if parent != '':
                    # Make sure the parent activity exists.
                    activities[parent].hpd = None
                    activities[parent].dpw = None

            except KeyError:
                sg.popup_ok('Chosen parent activity does not exist.', title='Error')
                continue

            # Add the new activity to the dict of all activities.
            new_key = new_values['-name-']
            activities[new_key] = new_activity
            if chosen_key != '' and chosen_key != new_key:
                del activities[chosen_key]
            window.close()
            return


def delete_activity(values, window, activities):
    if len(values['-data-']) == 0:
        sg.Popup('Select an activity to delete.', title='Error')
    else:
        chosen_key = values['-data-'][0]

        if not is_parent_activity(chosen_key, activities):
            choice = sg.popup_ok_cancel(f'Ready to delete "{chosen_key}".'
                                        '\nAre you sure?', title='Confirm')
            if choice == 'OK':
                del activities[chosen_key]
        else:
            choice = sg.popup_ok_cancel(f'Ready to delete "{chosen_key}"'
                                        'and all of its subactivities.'
                                        '\nAre you sure?', title='Confirm')
            if choice == 'OK':
                delete_subactivities(chosen_key, activities)


def is_parent_activity(chosen_key, activities):
    for key in activities:
        if activities[key].parent == chosen_key:
            return True
    return False


def delete_subactivities(chosen_key, activities):
    del activities[chosen_key]
    for key, _ in list(activities.items()):
        if activities[key].parent == chosen_key:
            delete_subactivities(key, activities)


def get_available_hours(activities):
    total_hpw = 0
    for key in activities:
        if activities[key].hpd is not None:
            total_hpw += activities[key].hpd * activities[key].dpw
    return 168 - total_hpw


def get_tree_data(activities):
    tree_data = sg.TreeData()
    errored_keys = []
    for key in activities:
        Hours = hours_to_strings(hours(activities, key))
        try:
            tree_data.insert(activities[key].parent,
                             key=key,
                             text=key,
                             values=Hours)
        except KeyError:
            errored_keys.append(key)

    while len(errored_keys) != 0:
        for key in errored_keys:
            if not key_exists(key, activities):
                raise KeyError

            Hours = hours_to_strings(hours(activities, key))
            try:
                tree_data.insert(activities[key].parent,
                                 key=key,
                                 text=key,
                                 values=Hours)
                errored_keys.remove(key)
            except KeyError:
                pass

    return tree_data


def key_exists(key, activities):
    for k in activities:
        if key == k:
            return True
    return False


# Return a tuple of hours per day, days per week, and hours per week.
def hours(activities, chosen_key):
    chosen = activities[chosen_key]

    # If the chosen activity is not a parent.
    if chosen.hpd is not None:
        hpw = chosen.hpd * chosen.dpw
        return chosen.hpd, chosen.dpw, hpw
    else:
        # Find the average hpd over 7 days for this activity.
        avg_hpd = 0
        total_hpw = 0
        for key in activities:
            if activities[key].parent == chosen_key:
                sub_h = hours(activities, key)
                hpw = sub_h[0] * sub_h[1]
                avg_hpd += round(hpw / 7, 2)
                total_hpw += hpw

        return avg_hpd, 7, total_hpw


# Return the inputs as strings without trailing zeros.
def hours_to_strings(hours):
    hpd = '{0:g}'.format(hours[0])
    dpw = '{0:g}'.format(hours[1])
    hpw = '{0:g}'.format(hours[2])
    return hpd, dpw, hpw


if __name__ == '__main__':
    main()
