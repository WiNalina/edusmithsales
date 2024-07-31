def create_space_index_list(str_in):
    list_output = list()
    for each_ind in range(len(str_in)):
        if str_in[each_ind] == ' ':
            list_output.append(each_ind)
    return list_output

def create_new_line_index_list(str_in):
    list_output = list()
    for each_ind in range(len(str_in)):
        if each_ind >= 1:
            if str_in[each_ind - 1] == '\\' and str_in[each_ind] == 'n':
                list_output.append(each_ind+1)
    return list_output

def process_note(str_in, limit_line_length=70):
    list_new_line_index = create_new_line_index_list(str_in)
    list_space_index = create_space_index_list(str_in)

    count_collected_string_length = 0
    if len(list_new_line_index) > 0:
        for each_list_index, each_new_line_index in enumerate(list_new_line_index):
            if each_list_index == 0:
                each_line_str = str_in[0:each_new_line_index - 2]
                count_collected_string_length += len(each_line_str) + 2
            elif each_list_index < len(list_new_line_index) - 1:
                each_line_str = str_in[list_new_line_index[each_list_index-1]: each_new_line_index - 2]
                count_collected_string_length += len(each_line_str) + 2
            else:
                each_line_str = str_in[each_new_line_index:]
                count_collected_string_length += len(each_line_str)

            list_output_str.append(each_line_str.strip())
    
    if count_collected_string_length == len(str_in):
        return list_output_str
    else:
        new_list_output_str = list()
        for each_ind in range(len(list_output_str)):
            if each_ind < len(list_output_str) - 1:
                new_list_output_str.append(list_output_str[each_ind])
            else:
                last_line_string = list_output_str[each_ind]
                if len(last_line_string) < limit_line_length:
                    return list_output_str
                else:
                    list_last_line_string = list()
                    while len(last_line_string) > limit_line_length:
                        last_line_space_index_list = create_space_index_list(last_line_string)
                        for each_space_index in last_line_space_index_list:
                            if each_space_index > limit_line_length:
                                list_last_line_string.append(last_line_string[:each_list_index])
                                break
                        last_line_string = last_line_string[each_list_index + 1:]
                    list_last_line_string.append(last_line_string)
                    new_list_output_str.extend(list_last_line_string)
                    
                    return new_list_output_str

                    
    

    
