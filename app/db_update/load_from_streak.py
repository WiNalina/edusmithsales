import pandas as pd
import numpy as np
import re
from app.db_update.process_score import process_score

import requests
import json

class load_from_streak:
    def __init__(self, student_box_url, pipeline_url, headers, auth_key, field_keyname='fields'):
        """ A class used for fetching the data from Streak

        Args:
            student_box_url (str): URL of the student boxes
            pipeline_url (str): URL of the pipeline
            headers (str): Header of the request
            auth_key (str): Authentication Key
            field_keyname (str, optional): Field string name. Defaults to 'fields'.
        """
        
        self.student_box_url = student_box_url
        self.pipeline_url = pipeline_url
        self.headers = headers
        self.auth_key = auth_key
        self.field_keyname = field_keyname
        self.all_students_dict = dict() #Dictionary for storing all students' information
        self.dict_target_colname = {
            'student_id': 'streak_id',
            'universal_id': 'universal_id',
            'name_in_thai': 'name_th',
            'school': 'school',
            'grad_year': 'graduate_year',
            
            "mobile_no.": 'mobile_num',
            'email': 'email',
            'line': 'line',
            "address": 'address',
            'tax_id': 'tax_id',
            
            "dad's_name": 'dad_name',
            "dad's_mobile_no.": 'dad_mobile_num',
            "dad's_email": 'dad_email',
            "dad's_line": 'dad_line',
            
            "mom's_name": 'mom_name',
            "mom's_mobile_no.": 'mom_mobile_num',
            "mom's_email": 'mom_email',
            "mom's_line": 'mom_line',
            
            'know_us_from': 'know_us_from'
        } #Dict for replacing column names - each key being the original column name and each value being the to-be-replaced column name

    def remove_parentheses(self, str_in):
        """Replace parentheses by blank spaces

        Args:
            str_in (str): string with parentheses

        Returns:
            (str): string with parentheses replaced
        """
        temp_str = re.sub(r'\(', '', str_in)
        temp_str = re.sub(r'\)', '', temp_str)
        return temp_str

    def count_slash(self, str_in):
        """Count the number of slashes found in the input string - used for formatting the string dates

        Args:
            str_in (str): string of date inputs

        Returns:
            int: number of slashes found in the input string
        """
        #Go over all of the characters in the string and count the number of slashes
        num_count_slash = 0
        for alphabet in str_in:
            if alphabet == '/':
                num_count_slash += 1
        return num_count_slash

    def process_date(self, str_in):
        """Find day, month, and year of the input date string

        Args:
            str_in (str): string of the input date

        Returns:
            int: day, month, and year of the input string
        """

        #Remove parentheses from the input string and change the input strings to the integer form
        temp_str = self.remove_parentheses(str_in)
        num_slash = self.count_slash(temp_str)
        list_str = temp_str.split('/')
        
        output_day = None
        output_month = None
        output_year = None
        
        if num_slash > 0:
            if num_slash == 2:
                output_day = int(list_str[0])
                output_month = int(list_str[1])
                if len(list_str[2]) == 4:
                    #For the case when the digits are in full form already
                    output_year = int(list_str[2])
                elif len(list_str[2]) == 2:
                    output_year = int(list_str[2]) + 2000
            elif num_slash == 1:
                output_month = int(list_str[0])
                output_year = int(list_str[1])
        
        return output_day, output_month, output_year

    def modify_colname(self, each_str):
        """Lower cases of all alphabets in the input string and change whitespaces in the string to underscores

        Args:
            each_str (str): input column name

        Returns:
            str: lower-case string with whitespaces changed to underscores
        """
        temp_str = each_str.lower()
        temp_str = re.sub(' ','_', temp_str)
        
        return temp_str

    def find_dict_name_and_code(self, field_in):
        """Find program, school, and grad year key names and codes

        Args:
            field_in (dict of dict): Dictionary of all fields from Streak

        Returns:
            tuple: tuples of names and codes found from the dictionary
        """
        program_key_name = None
        school_key_name = None
        gradyear_key_name = None
        
        program_key_code = None
        school_key_code = None
        gradyear_key_code = None

        #Go over all dictionaries in the input dictionary and check if the specifications match the target names and types
        for each_dict in field_in:
            each_name = each_dict['name'].lower()
            each_type = each_dict['type'].lower()

            if each_type == 'tag' and ('program' in each_name or 'service' in each_name):
                program_key_name = each_dict['name']
                program_key_code = each_dict['key']
            elif each_type == 'dropdown':
                if 'school' in each_name or 'college' in each_name:
                    school_key_name = each_dict['name']
                    school_key_code = each_dict['key']
                elif 'grad' in each_name and 'year' in each_name:
                    gradyear_key_name = each_dict['name']
                    gradyear_key_code = each_dict['key']
            else:
                if program_key_name is not None and program_key_code is not None and school_key_name is not None and school_key_code is not None and gradyear_key_name is not None and gradyear_key_code is not None:
                    break
                else:
                    pass
            
        #Output tuples for names and codes
        output_name_tuple = (program_key_name, school_key_name, gradyear_key_name)
        output_code_tuple = (program_key_code, school_key_code, gradyear_key_code)
        
        return output_name_tuple, output_code_tuple

    def read_student_boxes_and_pipeline(self):
        """
        Read student boxes and student pipeline from Streak
        """
        student_box_response = requests.request("GET", self.student_box_url, headers=self.headers, auth = (self.auth_key,''))
        self.student_boxes = json.loads(student_box_response.text)
        #Delete the student box response for RAM optimization
        del student_box_response

        pipeline_response = requests.request("GET", self.pipeline_url, headers=self.headers, auth = (self.auth_key,''))
        self.pipeline_all_info = json.loads(pipeline_response.text)
        #Delete the pipeline response for RAM optimization
        del pipeline_response

    def create_two_direction_dict(self, list_all_field_dicts):
        """Create two dictionaries with one having field keys as keys and field values as values and another dictionary with the keys with field values and the values being the field keys

        Args:
            list_all_field_dicts (list): [description]

        Returns:
            [type]: [description]
        """
        dict_field_index = dict()
        dict_field_key_to_value = dict()
        max_key_value = 0

        for each_ind, each_dict in enumerate(list_all_field_dicts):
            dict_field_index[each_dict['name']] = each_ind
            dict_field_key_to_value[each_dict['key']]= each_dict['name']
            if int(each_dict['key']) > max_key_value:
                max_key_value = int(each_dict['key'])

        if str(max_key_value - 1) not in dict_field_key_to_value:
            dict_field_key_to_value[str(max_key_value - 1)] = dict_field_key_to_value[str(max_key_value)]

        return dict_field_index, dict_field_key_to_value

    def dropdown_type_dict(self, dict_field_index, all_info_dicts, column_name, tag_flag = False):
        """ Create dictionaries of data needed for the dropdown data type in Streak

        Args:
            dict_field_index (dict): A dicitonary containing keys and values containing specific codes for all data
            all_info_dicts (dict): A dictionary containing the actual data seen in the json file
            column_name (str): A column name to be described for the output data frame
            tag_flag (bool, optional): A boolean describing whether the data seen are set as tags. If False, the data are in the dropdown type. Defaults to False.

        Returns:
            [type]: [description]
        """
        if tag_flag:
            first_order_key, second_order_key, subdict_key = 'tagSettings', 'tags', 'tag'
        else:
            first_order_key, second_order_key, subdict_key = 'dropdownSettings', 'items', 'name'

        dict_index = dict_field_index[column_name]
        dict_target = all_info_dicts[self.field_keyname][dict_index][first_order_key][second_order_key]

        dict_output = dict()
        for each_subdict in dict_target:
            dict_output[each_subdict['key']] = each_subdict[subdict_key]

        return dict_output

    def create_program_school_gradyear_dict(self, list_all_field_dicts, dict_field_index, all_info_dicts):
        """Create two dictionaries of programs, schools, and graduation years with one having keys being object names and values being codes found from Streak, and the other one having keys being codes from Streak and values being object names 

        Args:
            list_all_field_dicts (list): list of all fields found from Streak
            dict_field_index (dict): dictionary of all field indices from Streak
            all_info_dicts (dict): dictionary of all information retrieved from Streak
        """
        #Create tuples of object codes and names with each element being a tuple of program objects, a tuple of school objects, and a tuple of graduation years
        name_tuple, code_tuple = self.find_dict_name_and_code(list_all_field_dicts)
        
        #Define each variable using the information from the tuples
        self.program_column_name, self.school_column_name, self.gradyear_column_name = name_tuple[0], name_tuple[1], name_tuple[2]
        self.program_column_code, self.school_column_code, self.gradyear_column_code = code_tuple[0], code_tuple[1], code_tuple[2]

        #Deal with the program dictionary and the school dictionary, and the graduation dictionary as the input has the dropdown type 
        self.dict_program = self.dropdown_type_dict(dict_field_index, all_info_dicts, column_name=self.program_column_name, tag_flag = True)
        self.dict_school = self.dropdown_type_dict(dict_field_index, all_info_dicts, column_name=self.school_column_name, tag_flag = False)
        self.dict_gradyear = self.dropdown_type_dict(dict_field_index, all_info_dicts, column_name=self.gradyear_column_name, tag_flag = False)

    def create_int_key_dict(self, dict_in):
        """Create a dictionary with a key being an integer rather than a string - used for the program dictionary

        Args:
            dict_in (dict): input dictionary - used for the program dict

        Returns:
            dict: program dict with each key having the integer type
        """
        dict_program_int_key = dict()
        for each_key in dict_in:
            dict_program_int_key[int(each_key)] = dict_in[each_key]
        return dict_program_int_key

    def create_dicts_from_dropdowns(self):
        """
        Create a dictionary of all information from the fields collecting data in the form of dropdown field
        """
        list_all_field_dicts = self.pipeline_all_info[self.field_keyname]
        dict_field_index, self.dict_field_key_to_value = self.create_two_direction_dict(list_all_field_dicts)
        self.create_program_school_gradyear_dict(list_all_field_dicts, dict_field_index, self.pipeline_all_info)
        self.dict_program_int_key = self.create_int_key_dict(self.dict_program)
        
    def extract_dropdown_info_for_student_dict(self, dict_in, column_code, dict_in_int_key=None, must_have_flag=False):
        """Generate a list of all information extracted from the input dictionary obtained from each category

        Args:
            dict_in (dict): A dictionary from each field
            column_code (int): Integer indicating each column's code
            dict_in_int_key (dict, optional): A dictionary with each key being having integer type rather than string type. Defaults to None.
            must_have_flag (bool, optional): A boolean indicating if the column must exist - if so, it will report all of the missing values in another variable called problem set. Defaults to False.

        Returns:
            temp_list (list): A list of all values found from the given dictionary
            problem_set (set): A set of all problematic values found from the given dictionary
        """

        temp_list = list()
        problem_set = set()

        #Two cases - the must-have case will populate the problem set with the original dict, while the other will look up from both the original dict and the dict with keys being integer
        if must_have_flag:
            for each_value in self.all_students_dict[column_code]:
                #Go over each value and populate the temp_list with the information from dict_in. If it doesn't exist, put 'NaN' in it and populate the problem_set instead
                if each_value in dict_in:
                    temp_list.append(dict_in[each_value])
                else:
                    temp_list.append('NaN')
                    problem_set.add(each_value)
            return temp_list, problem_set
        
        else:
            #Otherwise, look up from the two dictionaries - one being the original dict and the other being the dict with integer keys
            for each_list in self.all_students_dict[column_code]:
                temp_each_list = list()
                if isinstance(each_list, list):
                    if len(each_list) > 0:
                        for each_code in each_list:
                            if each_code in dict_in:
                                temp_each_list.append(dict_in[each_code])
                            elif dict_in_int_key is not None and isinstance(dict_in_int_key, dict):
                                if each_code in dict_in_int_key:
                                    temp_each_list.append(dict_in_int_key[each_code])
                            else:
                                #If the data are not found in both dicts, add them to the problem set
                                problem_set.add(each_code)
                #Append each temporary list to the output list
                temp_list.append(temp_each_list)
        
            return temp_list, problem_set

    def build_student_dict(self):
        """
        Build a dict with each key being each original data frame's column name and each value being list containing each student's information regarding the column
        """
        #Collect a set of all original fields in set_all_orig_fields
        set_all_orig_fields = set()
        for each_dict in self.student_boxes:
            field_dict = each_dict['fields']
            for each_key in field_dict:
                set_all_orig_fields.add(each_key)

        #Add name and all columns to the dictionary
        self.all_students_dict['name'] = list()
        for each_col in set_all_orig_fields:
            if each_col not in self.all_students_dict:
                self.all_students_dict[each_col] = list()
        
        #Go over each dict in the student boxes and append each column value to each list for the column in in our self.all_student_dict - otherwise append 'NaN' instead
        for each_dict in self.student_boxes:
            self.all_students_dict['name'].append(each_dict['name'])
            set_cols_added = {'name'}
            
            for each_col in each_dict['fields']:
                self.all_students_dict[each_col].append(each_dict['fields'][each_col])
                set_cols_added.add(each_col)
            
            for each_col in set_all_orig_fields:
                if each_col not in set_cols_added:
                    self.all_students_dict[each_col].append('NaN')
        
        #Program fits the optional case
        temp_program_list, self.problem_program_set = self.extract_dropdown_info_for_student_dict(self.dict_program, self.program_column_code, dict_in_int_key=self.dict_program_int_key, must_have_flag=False)
        #School and graduation year fit the mandatory cases
        temp_gradyear_list, self.problem_gradyear_set = self.extract_dropdown_info_for_student_dict(self.dict_gradyear, self.gradyear_column_code, dict_in_int_key=None, must_have_flag=True)
        temp_school_list, self.problem_school_set = self.extract_dropdown_info_for_student_dict(self.dict_school, self.school_column_code, dict_in_int_key=None, must_have_flag=True)

        #Assign the values to the target dict
        self.all_students_dict[self.program_column_code] = temp_program_list
        self.all_students_dict[self.gradyear_column_code] = temp_gradyear_list
        self.all_students_dict[self.school_column_code] = temp_school_list

    def create_rename_dict(self):
        """Create a dictionary used for renaming the data columns and a list used for scoping down the final columns to be included in the output

        Returns:
            dict_rename (dict): dict for renaming the columns
            list_colname_selected (list): list of column names to be included in the final output 
        """
        dict_rename = dict()
        list_colname_selected = ['name', 'previous_scores']
        
        #Add each final column name from the dict_target_colname to the list_colname_selected
        for each_col in self.dict_target_colname:
            list_colname_selected.append(self.dict_target_colname[each_col])
        
        #Go over the dict and create keys being the original column names and the values being the final column names
        for each_key in self.dict_field_key_to_value:
            each_colname = self.modify_colname(self.dict_field_key_to_value[each_key])
            if each_colname in self.dict_target_colname:
                dict_rename[each_key] = self.dict_target_colname[each_colname]
            else:
                dict_rename[each_key] = each_colname

        return dict_rename, list_colname_selected
        
    def clean_edge_case_string(self, df_in):
        """Clean nan values to be np.nan and new line characters to be just a white space

        Args:
            df_in (pd.DataFrame): input data frame

        Returns:
            pd.DataFrame: Cleaned data frame
        """
        df_in = df_in.replace({'NaN', np.nan})
        df_in = df_in.replace(r'\n',' ', regex=True)
        
        return df_in
    
    def cast_to_type(self, df_in, colname, datatype):
        #Cast a specific column of the input data frame to the target data type
        df_in.loc[:,colname] = df_in.loc[:,colname].astype(datatype)
        return df_in

    def create_student_df(self, student_country, student_country_colname):
        """Create a final student data frame with the indicated country being a column in this data frame

        Args:
            student_country (str): a string of student country
            student_country_colname (str): a column name for the student country field
        """
        #Read the original student boxes and extract the data from them
        self.read_student_boxes_and_pipeline()
        self.create_dicts_from_dropdowns()
        self.build_student_dict()
        dict_rename, list_colname_selected = self.create_rename_dict()
        
        #Create a data frame of student information and clean it in order to fit our requirements
        self.student_df = pd.DataFrame(self.all_students_dict)
        self.student_df = self.student_df.rename(columns = dict_rename)
        self.student_df = self.student_df[self.student_df.columns.intersection(list_colname_selected)]
        self.student_df = self.clean_edge_case_string(self.student_df)
        self.student_df = self.cast_to_type(self.student_df, 'universal_id', int)

        #Set the student country as described by the input
        self.student_df[student_country_colname] = student_country
        del self.all_students_dict

    def create_test_score_df(self):
        #Use the process_score function to create a data frame of all test_scores
        test = process_score(self.student_df['previous_scores'], self.student_df[['name', 'universal_id']])
        self.test_score_df = test.process_all()
        
