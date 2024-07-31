import re
import pandas as pd
import datetime

class process_score:
    """
    Process all of the test scores in the input student data frame (student_info_df)
    """
    def __init__(self, series_in, student_info_df = None):
        #series_in being a column of all previous test scores
        #student_info_df being a data frame of names and universal ids for all students
        self.series_in = series_in
        self.student_info_df = student_info_df
        self.dict_all_students = dict() #dictionary of all students' exams - will become the output dict
        self.dict_each_student = dict() #dictionary of each student's exam scores
        self.str_list = list() #A list of exam details in the form of string list
        self.removed_str_set = {'=', '\n'} #A set of strings to be removed
        #A dict to replace months from the input information
        self.dict_month_name_to_ind = {
            'jan': 1,
            'feb': 2,
            'mar': 3,
            'apr': 4,
            'may': 5,
            'jun': 6,
            'jul': 7,
            'aug': 8,
            'sep': 9,
            'oct': 10,
            'nov': 11,
            'dec': 12
        }
        self.output_df_column_order_list = ['name','universal_id', 'exam_name', 'exam_type', 'exam_date', 'mock_flag'] #A list of strings for columns
        self.sat_score_type_list = ['reading_score', 'writing_score', 'reading_writing_score', 'quant_score', 'total_score'] #A list of SAT score types
        self.subject_test_score_type_list = ['subject_test_physics_score', 'subject_test_chemistry_score', 'subject_test_biology_e_score', 'subject_test_biology_m_score', 'subject_test_math_lvl_1_score', 'subject_test_math_lvl_2_score', 'subject_test_literature_score', 'subject_test_us_history_score', 'subject_test_world_history_score', 'subject_test_language_score'] #A list of SAT Subject Test score types
        self.ssat_score_type_list = ['reading_score', 'verbal_score', 'quant_score', 'percentile'] #A list of SSAT score types
        self.psat_score_type_list = ['reading_score', 'writing_score', 'reading_writing_score', 'quant_score', 'total_score'] #A list of PSAT score types
        self.act_score_type_list = ['reading_score', 'act_english_score', 'math_score', 'act_science_score', 'act_composite_score'] #A list of ACT score types
        self.toefl_overall_score_type_list = ['reading_score', 'writing_score', 'listening_score', 'speaking_score', 'total_score', 'toefl_itp_grammar_score'] #A list of universal TOEFL score types
        self.toefl_ibt_score_type_list = ['reading_score', 'writing_score', 'listening_score', 'speaking_score', 'total_score'] #A list of TOEFL iBT score types
        self.toefl_itp_score_type_list = ['reading_score', 'writing_score', 'listening_score', 'toefl_itp_grammar_score'] #A list of TOEFL ITP score types
        self.ietls_score_type_list = ['reading_score', 'writing_score', 'listening_score', 'speaking_score', 'total_score'] #A list of IELTS score types
        self.gre_score_type_list = ['verbal_score', 'writing_score', 'quant_score', 'total_score'] #A list of GRE score types
        self.gmat_score_type_list = ['verbal_score', 'gmat_verbal_percentile_score', 'quant_score', 'gmat_quant_percentile_score', 'total_score'] #A list of GMAT score types
        self.bmat_score_type_list = ['bmat_part_1_score', 'bmat_part_2_score', 'bmat_part_3_content_score', 'bmat_part_3_grammar_score'] #A list of BMAT score types
        self.unknown_score_type_list = ['unknown_exam_info'] 

    def examnamefilter(self, value):
        """Change the input string value to the string of the target exam name

        Args:
            value (str): A string of exam name

        Returns:
            str: A string of intended exam name
        """
        if value == 'toefl':
            return 'TOEFL'
        elif value == 'ielts':
            return 'IELTS'
        elif value == 'sat':
            return 'SAT'
        elif value == 'ssat':
            return 'SSAT'
        elif value == 'psat':
            return 'PSAT'
        elif value == 'subject_test':
            return 'SAT Subject Test'
        elif value == 'act':
            return 'ACT'
        elif value == 'gmat':
            return 'GMAT'
        elif value == 'BMAT':
            return 'BMAT'
        elif value == 'unknown' or value == 'nan':
            return 'UNKNOWN'
        else:
            return value

    def examtypefilter(self, value):
        """Change the input string value to the string of the target exam type

        Args:
            value (str): A string of exam type

        Returns:
            str: A string of intended exam type
        """
        if value == 'itp':
            return 'ITP'
        elif value == 'ibt':
            return 'IBT'
        elif value == 'upper':
            return 'Upper'
        elif value == 'middle':
            return 'Middle'
        elif value == 'unknown' or value == 'nan':
            return 'Unknown'
        else:
            return value

    def scoretypefilter(self, value):
        """Change the input string value to the string of the target score type

        Args:
            value (str): A string of score type

        Returns:
            str: A string of intended score type
        """
        #TOEFL/IELTS
        if value == 'reading':
            return 'Reading'
        elif value == 'writing':
            return 'Writing'
        elif value == 'listening':
            return 'Listening'
        elif value == 'speaking':
            return 'Speaking'
        elif value == 'toefl_itp_grammar':
            return 'Grammar'

        #SAT/SSAT/PSAT
        elif value == 'reading_writing':
            return 'Reading & Writing'
        elif value == 'quant' or value == 'gmat_quant_percentile':
            return 'Quant/Math'
        elif value == 'verbal' or value == 'gmat_verbal_percentile':
            return 'Verbal'
        elif value == 'percentile':
            return 'Percentile'

        #ACT
        elif value == 'act_english':
            return 'English'
        elif value == 'math':
            return 'Math'
        elif value == 'act_science':
            return 'Science'
        elif value == 'act_composite':
            return 'Composite'

        #SAT Subject Test
        elif value == 'subject_test_physics':
            return 'Physics'
        elif value == 'subject_test_chemistry':
            return 'Chemistry'
        elif value == 'subject_test_biology_e':
            return 'Biology E'
        elif value == 'subject_test_biology_m':
            return 'Biology M'
        elif value == 'subject_test_math_lvl_1':
            return 'Math Level 1'
        elif value == 'subject_test_math_lvl_2':
            return 'Math Level 2'
        elif value == 'subject_test_literature':
            return 'Literature'
        elif value == 'subject_test_us_history':
            return 'US History'
        elif value == 'subject_test_world_history':
            return 'World History'
        elif value == 'subject_test_language':
            return 'Foreign Language'

        #BMAT
        elif value == 'bmat_part_1':
            return 'BMAT Part 1'
        elif value == 'bmat_part_2':
            return 'BMAT Part 2'
        elif value == 'bmat_part_3_content':
            return 'BMAT Part 3 - Content'
        elif value == 'bmat_part_3_grammar':
            return 'BMAT Part 3 - Grammar'

        #Total
        elif value == 'total':
            return 'Total Score'

        #If not fitted to any case here, return the original value
        else:
            return value
        
    def clean_str_in(self, str_in):
        """Clean the input string by separating strings with ';', lower them, remove strings as described in self.removed_str_set, strip them, and add the string to the self.str_list

        Args:
            str_in (str): An input string
        """
        #Split by ';'
        temp_str_list = str_in.split(';')
        #Go over each component in temp_str_list
        for each_str in temp_str_list:
            #Lower each string
            cleaned_str = each_str.lower()
            for each_removed_str in self.removed_str_set:
                #Remove strings as given in the removed_str_set
                cleaned_str = re.sub(each_removed_str, '', cleaned_str)

            #Add the cleaned string to the str_list
            self.str_list.append(cleaned_str.strip())

    def assign_missing_score(self, dict_in, score_type_list):
        """Assign missing values (None) for the score types that are missing for each exam

        Args:
            dict_in (dict): A dictionary of each test score
            score_type_list (list): list of score types

        Returns:
            dict: A dictionary with all test scores filled in the dict as keys
        """
        for each_score in score_type_list:
            if each_score not in dict_in:
                dict_in[each_score] = None
        return dict_in

    def find_date_month(self, str_in):
        """Find the month of the given date from the input string (str_in)

        Args:
            str_in (str): input string

        Returns:
            float: month index of the input date
        """
        if str_in in self.dict_month_name_to_ind:
            return self.dict_month_name_to_ind[str_in]
        elif re.match(r'^[0-9]{2}$', str_in) or re.match(r'^[0-9]{1}$', str_in):
            return float(str_in)
        else:
            return None
            
    def find_date_year(self, str_in):
        """Find the year of the given date from the input string (str_in)

        Args:
            str_in (str): input string

        Returns:
            float: year of the input date
        """
        if re.match(r'^[0-9]{4}$', str_in):
            return float(str_in)
        elif re.match(r'^[0-9]{2}$', str_in):
            return 2000 + float(str_in)
        else:
            return None

    def convert_float_to_int(self, val_in):
        #Convert input value from float to int
        if isinstance(val_in, float):
            return int(val_in)

    def check_date(self, str_in):
        """Check if the given string is a date. If so, find the day, month, and year of the date

        Args:
            str_in (str): Date string

        Returns:
            output_day (int): output day of the month
            output_month (int): output month of the year
            output_year (int): output year
        """
        output_day = None
        output_month = None
        output_year = None

        str_in_list = str_in.split() #Split by space into a list of strings

        for each_str in str_in_list:
            #Find a string having parentheses at the beginning and the end
            match_obj = re.match(r'^\((.+)\)$', each_str)
            if match_obj:
                #Extract outputs given the number of slashes
                date_str = match_obj.group(1)
                num_slash = date_str.count('/')
                if num_slash >= 1:
                    #One slash = year and month
                    temp_list = date_str.split('/')
                    if num_slash == 1:
                        if float(temp_list[0]) <= 12:
                            output_year = self.find_date_year(temp_list[1])
                            output_month = float(temp_list[0])
                    elif num_slash == 2:
                        #Two slashes = year, month, and day
                        output_year = self.find_date_year(temp_list[2])
                        
                        if float(temp_list[0]) > 12:
                            output_day = float(temp_list[0])
                            output_month = float(temp_list[1])
                        else:
                            output_month = float(temp_list[0])
                            output_day = float(temp_list[1])
                else:
                    #The other case happens when only month and year exist - e.g. Jan2020
                    find_long_year_case = re.search(r'[a-z]{3}[0-9]{4}', date_str)
                    find_short_year_case = re.search(r'[a-z]{3}[0-9]{2}', date_str)
                    
                    if find_long_year_case:
                        #Find the case when years match the 20xx pattern - such as Jan2021
                        full_text = find_long_year_case.group()
                        output_month = self.dict_month_name_to_ind[full_text[:3]]
                        output_year = float(full_text[3:])
                    elif find_short_year_case:
                        #Find the case when years match the short pattern - such as Jan21
                        full_text = find_long_year_case.group()
                        output_month = self.dict_month_name_to_ind[full_text[:3]]
                        output_year = 2000 + float(full_text[3:])
            if output_month is not None or output_year is not None:
                #If we have already matched the month and the year, just break the loop
                break
        
        #Convert the outputs from floats to integers
        output_day = self.convert_float_to_int(output_day)
        output_month = self.convert_float_to_int(output_month)
        output_year = self.convert_float_to_int(output_year)

        return output_day, output_month, output_year
    

    def process_sat(self, str_in, exam_ind):
        """Process the SAT score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.sat_score_type_list #Prepare the score type list
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^r[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['reading_score'] = float(each_str[1:])
            elif re.match(r'^w[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['writing_score'] = float(each_str[1:])
            elif re.match(r'^rw[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['reading_writing_score'] = float(each_str[2:])
            elif re.match(r'^m[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['quant_score'] = float(each_str[1:])
            elif re.match(r'^t[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['total_score'] = float(each_str[1:])

        #Handle the reading & writing scores combined together
        if 'reading_writing_score' not in self.dict_each_student[exam_ind]:
            if 'reading_score' in self.dict_each_student[exam_ind] and 'writing_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['reading_writing_score'] = self.dict_each_student[exam_ind]['reading_score'] + self.dict_each_student[exam_ind]['writing_score']

        #Handle the total scores combined together from multiple subscores
        if 'total_score' not in self.dict_each_student[exam_ind]:
            if 'reading_score' in self.dict_each_student[exam_ind] and 'writing_score' in self.dict_each_student[exam_ind] and 'quant_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['total_score'] = self.dict_each_student[exam_ind]['reading_score'] + self.dict_each_student[exam_ind]['writing_score'] + self.dict_each_student[exam_ind]['quant_score']
            elif 'reading_writing_score' in self.dict_each_student[exam_ind] and 'quant_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['total_score'] = self.dict_each_student[exam_ind]['reading_writing_score'] + self.dict_each_student[exam_ind]['quant_score']

        #Assign None for missing scores
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)
        

    def process_subject_test(self, str_in, exam_ind):
        """Process the SAT Subject score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.subject_test_score_type_list #Prepare the score type list
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^p[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_physics_score'] = float(each_str[1:])
            elif re.match(r'^c[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_chemistry_score'] = float(each_str[1:])
            elif re.match(r'^be[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_biology_e_score'] = float(each_str[1:])
            elif re.match(r'^bm[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_biology_m_score'] = float(each_str[1:])
            elif re.match(r'^mi[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_math_lvl_1_score'] = float(each_str[1:])
            elif re.match(r'^mii[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_math_lvl_2_score'] = float(each_str[1:])
            elif re.match(r'^li[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_literature_score'] = float(each_str[1:])
            elif re.match(r'^us[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_us_history_score'] = float(each_str[1:])
            elif re.match(r'^wh[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_world_history_score'] = float(each_str[1:])
            elif re.match(r'^la[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['subject_test_language_score'] = float(each_str[1:])
            
        #Assign None for missing scores
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)
            

    def check_ssat_type(self, str_in, exam_ind):
        """Find SSAT subtype

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        if re.search(r'middle', str_in):
            self.dict_each_student[exam_ind]['exam_type'] = 'middle'
        elif re.search(r'upper', str_in):
            self.dict_each_student[exam_ind]['exam_type'] = 'upper'
        else:
            self.dict_each_student[exam_ind]['exam_type'] = 'nan'


    def process_ssat(self, str_in, exam_ind):
        """Process the SSAT score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        self.check_ssat_type(str_in, exam_ind) #Check SSAT type
        score_type_list = self.ssat_score_type_list #Prepare the score type list
        
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^r[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['reading_score'] = float(each_str[1:])
            elif re.match(r'^v[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['verbal_score'] = float(each_str[1:])
            elif re.match(r'^q[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['quant_score'] = float(each_str[1:])
            elif re.match(r'^p[0-9]{2}$', each_str) or re.match(r'^p[0-9]{1}$', each_str):
                self.dict_each_student[exam_ind]['percentile'] = float(each_str[1:])
        
        #Assign None for missing scores
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)

    def check_psat_type(self, str_in, exam_ind):
        """Find PSAT subtype

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        if re.search(r'middle', str_in):
            self.dict_each_student[exam_ind]['exam_type'] = 'middle'
        elif re.search(r'upper', str_in):
            self.dict_each_student[exam_ind]['exam_type'] = 'upper'
        else:
            self.dict_each_student[exam_ind]['exam_type'] = 'nan'


    def process_psat(self, str_in, exam_ind):
        """Process the PSAT score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        self.check_psat_type(str_in, exam_ind) #Check the PSAT exam type
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.psat_score_type_list #Prepare the score type list

        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^r[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['reading_score'] = float(each_str[1:])
            elif re.match(r'^w[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['writing_score'] = float(each_str[1:])
            elif re.match(r'^rw[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['reading_writing_score'] = float(each_str[2:])
            elif re.match(r'^m[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['quant_score'] = float(each_str[1:])
            elif re.match(r'^t[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['total_score'] = float(each_str[1:])

        #Handle the reading & writing scores combined together
        if 'reading_writing_score' not in self.dict_each_student[exam_ind]:
            if 'reading_score' in self.dict_each_student[exam_ind] and 'writing_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['reading_writing_score'] = self.dict_each_student[exam_ind]['reading_score'] + self.dict_each_student[exam_ind]['writing_score']

        #Handle the total scores combined together from multiple subscores
        if 'total_score' not in self.dict_each_student[exam_ind]:
            if 'reading_score' in self.dict_each_student[exam_ind] and 'writing_score' in self.dict_each_student[exam_ind] and 'quant_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['total_score'] = self.dict_each_student[exam_ind]['reading_score'] + self.dict_each_student[exam_ind]['writing_score'] + self.dict_each_student[exam_ind]['quant_score']
            elif 'reading_writing_score' in self.dict_each_student[exam_ind] and 'quant_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['total_score'] = self.dict_each_student[exam_ind]['reading_writing_score'] + self.dict_each_student[exam_ind]['quant_score']
        
        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)


    def process_act(self, str_in, exam_ind):
        """Process the ACT score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.act_score_type_list #Prepare the score type list
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^e[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['act_english_score'] = float(each_str[1:])
            elif re.match(r'^m[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['math_score'] = float(each_str[1:])
            elif re.match(r'^r[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['reading_score'] = float(each_str[1:])
            elif re.match(r'^s[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['act_science_score'] = float(each_str[1:])
            elif re.match(r'^c[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['act_composite_score'] = float(each_str[1:])

        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)

    def check_toefl_type(self, str_in, exam_ind):
        """Find TOEFL subtype

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        if re.search(r'ibt', str_in):
            self.dict_each_student[exam_ind]['exam_type'] = 'ibt'
        elif re.search(r'itp', str_in):
            self.dict_each_student[exam_ind]['exam_type'] = 'itp'
        else:
            self.dict_each_student[exam_ind]['exam_type'] = 'nan'


    def process_toefl(self, str_in, exam_ind):
        """Process the TOEFL score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        self.check_toefl_type(str_in, exam_ind) #Check the TOEFL exam type
        score_type_list = self.toefl_overall_score_type_list #Prepare the score type list
        
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^l[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['listening_score'] = float(each_str[1:])
            elif re.match(r'^w[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['writing_score'] = float(each_str[1:])
            elif re.match(r'^r[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['reading_score'] = float(each_str[1:])
            elif re.match(r'^s[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['speaking_score'] = float(each_str[1:])
            elif re.match(r'^t[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['total_score'] = float(each_str[1:])
            elif re.match(r'^g[0-9]+$', each_str):
                self.dict_each_student[exam_ind]['toefl_itp_grammar_score'] = float(each_str[1:])
        
        #Handle the total scores combined together from multiple subscores
        if 'total_score' not in self.dict_each_student[exam_ind] and self.dict_each_student[exam_ind]['exam_type'] == 'ibt':
            if 'listening_score' in self.dict_each_student[exam_ind] and 'writing_score' in self.dict_each_student[exam_ind] and 'reading_score' in self.dict_each_student[exam_ind] and 'speaking_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['total_score'] = self.dict_each_student[exam_ind]['listening_score'] + self.dict_each_student[exam_ind]['writing_score'] + self.dict_each_student[exam_ind]['reading_score'] + self.dict_each_student[exam_ind]['speaking_score']

        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)

    def process_ielts(self, str_in, exam_ind):
        """Process the IETLS score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.ietls_score_type_list #Prepare the score type list
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^l[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['listening_score'] = float(each_str[1:])
            elif re.match(r'^w[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['writing_score'] = float(each_str[1:])
            elif re.match(r'^r[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['reading_score'] = float(each_str[1:])
            elif re.match(r'^s[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['speaking_score'] = float(each_str[1:])
            elif re.match(r'^t[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['total_score'] = float(each_str[1:])

        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)

    def process_gre(self, str_in, exam_ind):
        """Process the GRE score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.gre_score_type_list #Prepare the score type list
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^v[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['verbal_score'] = float(each_str[1:])
            elif re.match(r'^q[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['quant_score'] = float(each_str[1:])
            elif re.match(r'^w[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['writing_score'] = float(each_str[1:])
            elif re.match(r'^t[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['total_score'] = float(each_str[1:])
        
        #Handle the total scores combined together from multiple subscores
        if 'total_score' not in self.dict_each_student[exam_ind]:
            if 'verbal_score' in self.dict_each_student[exam_ind] and 'quant_score' in self.dict_each_student[exam_ind]:
                self.dict_each_student[exam_ind]['total_score'] = self.dict_each_student[exam_ind]['verbal_score'] + self.dict_each_student[exam_ind]['quant_score']

        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)

    def process_gmat(self, str_in, exam_ind):
        """Process the GMAT score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.gmat_score_type_list #Prepare the score type list
        
        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^v[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['verbal_score'] = float(each_str[1:])
            elif re.match(r'^v[0-9]+[.]*[0-9]*%$', each_str):
                self.dict_each_student[exam_ind]['gmat_verbal_percentile_score'] = float(each_str[1:-1])
            elif re.match(r'^q[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['quant_score'] = float(each_str[1:])
            elif re.match(r'^v[0-9]+[.]*[0-9]*%$', each_str):
                self.dict_each_student[exam_ind]['gmat_quant_percentile_score'] = float(each_str[1:-1])
            elif re.match(r'^t[0-9]{3}$', each_str):
                self.dict_each_student[exam_ind]['total_score'] = float(each_str[1:])
        
        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)


    def process_bmat(self, str_in, exam_ind):
        """Process the BMAT score from the input string and assign the output in the [exam_ind]th index of self.dict_each_student

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        temp_str_list = str_in.split(' ') #Split the strings by spaces
        score_type_list = self.bmat_score_type_list #Prepare the score type list

        #Find the scores according to the regex patterns
        for each_str in temp_str_list:
            if re.match(r'^part1:[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['bmat_part_1_score'] = float(each_str[6:])
            elif re.match(r'^part2:[0-9]+[.]*[0-9]*$', each_str):
                self.dict_each_student[exam_ind]['bmat_part_2_score'] = float(each_str[6:])
            elif re.match(r'^part3:([0-9]+[.]*[0-9]*)([a-z]{1})$', each_str):
                match_obj = re.match(r'^part3:([0-9]+[.]*[0-9]*)([a-z]{1})$', each_str)
                self.dict_each_student[exam_ind]['bmat_part_3_content_score'] = float(match_obj.group(1))
                self.dict_each_student[exam_ind]['bmat_part_3_grammar_score'] = match_obj.group(2)
        
        #Handle missing scores by assigning None to them
        self.dict_each_student[exam_ind] = self.assign_missing_score(self.dict_each_student[exam_ind], score_type_list)

    def detect_exam_type(self, str_in, exam_ind):
        """Check if the exam is a mock exam and detect the exam type

        Args:
            str_in (str): String of exam information
            exam_ind (int): Index in the output dictionary to store the output exam info
        """
        #Check if the exam is a mock exam
        if re.search(r'mock', str_in):
            self.dict_each_student[exam_ind]['mock_flag'] = True
        else:
            self.dict_each_student[exam_ind]['mock_flag'] = False
        
        #Find the exam names and process the exams accordingly
        if re.search(r'ssat', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'ssat'
            self.process_ssat(str_in, exam_ind)
        
        elif re.search(r'psat', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'psat'
            self.process_psat(str_in, exam_ind)
        
        elif re.search(r's{0}sat', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'sat'
            self.process_sat(str_in, exam_ind)
        
        elif re.search(r'subject-test', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'subject_test'
            self.process_subject_test(str_in, exam_ind)

        elif re.search(r'act', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'act'
            self.process_act(str_in, exam_ind)

        elif re.search(r'toefl', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'toefl'
            self.process_toefl(str_in, exam_ind)

        elif re.search(r'ielts', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'ielts'
            self.process_ielts(str_in, exam_ind)

        elif re.search(r'gre', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'gre'
            self.process_gre(str_in, exam_ind)
        
        elif re.search(r'gmat', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'gmat'
            self.process_gmat(str_in, exam_ind)

        elif re.search(r'bmat', str_in):
            self.dict_each_student[exam_ind]['exam_name'] = 'bmat'
            self.process_bmat(str_in, exam_ind)
        
        else:
            #Handle the unknown case
            self.dict_each_student[exam_ind]['exam_name'] = 'unknown'
            self.dict_each_student[exam_ind]['unknown_exam_info'] = str_in

    def find_exam_info(self):
        """
        Find all exam info from type, score to date
        """
        #Go over all strings in the list
        for exam_ind, each_str in enumerate(self.str_list):
            self.dict_each_student[exam_ind] = dict()
            self.detect_exam_type(each_str, exam_ind) #Detect the exam type
            each_day, each_month, each_year = self.check_date(each_str) #Find the dates
            self.dict_each_student[exam_ind]['exam_day'] = each_day #Assign the dates
            self.dict_each_student[exam_ind]['exam_month'] = each_month
            self.dict_each_student[exam_ind]['exam_year'] = each_year

            if each_day is not None and each_month is not None and each_year is not None:
                #Create datetime object for the case when all date info exists
                date_obj = datetime.datetime(each_year, each_month, each_day)
                self.dict_each_student[exam_ind]['exam_date'] = date_obj
            
    
    def process_raw_string(self, str_in):
        """Clean and find all exam info in the input string

        Args:
            str_in (str): String of exam information
        """
        self.clean_str_in(str_in)
        self.find_exam_info()

    def reset_each_student_info(self):
        #Reset all information about each student
        self.dict_each_student = dict()
        self.str_list = list()

    def process_series_in(self):
        """Process the input series of exam strings

        Raises:
            ValueError: self.student_info_df must be a data frame 
        """
        if isinstance(self.student_info_df, pd.DataFrame):
            student_info_columns = self.student_info_df.columns
        else:
            raise ValueError('student_info_df must be a pd.DataFrame')

        for index, value in self.series_in.items():
            #Go over all items in the input series
            self.dict_all_students[index] = dict()
            if value == 'NaN':
                pass
            else:
                self.process_raw_string(value) #Process each value in the series
                #Create a dict of all students using the student_info_df
                if isinstance(self.student_info_df, pd.DataFrame):
                    for each_exam_key in self.dict_each_student:
                        for each_column in student_info_columns:
                            self.dict_each_student[each_exam_key][each_column] = self.student_info_df.loc[index, each_column]
                self.dict_all_students[index] = self.dict_each_student.copy()
                self.reset_each_student_info()
    
    def create_df_from_series(self):
        """
        Create an output data frame from the exam info series
        """
        all_colname_set = set()

        #Find all needed column names to create a set of all column names
        for each_student_key in self.dict_all_students:
            for each_exam_key in self.dict_all_students[each_student_key]:
                temp_exam_dict = self.dict_all_students[each_student_key][each_exam_key]
                for each_key in temp_exam_dict.keys():
                    if each_key not in all_colname_set:
                        all_colname_set.add(each_key)

        #Create a dict collecting all columns
        exam_score_dict = dict()
        for each_col in all_colname_set:
            exam_score_dict[each_col] = list()
            
        #Go over all students and create a dict to collect all information about each student's exam
        for each_student_key in self.dict_all_students:
            for each_exam_key in self.dict_all_students[each_student_key]:
                temp_exam_dict = self.dict_all_students[each_student_key][each_exam_key]
                temp_set = set()
                for each_exam_info_key in temp_exam_dict.keys():
                    temp_set.add(each_exam_info_key)
                    exam_score_dict[each_exam_info_key].append(self.dict_all_students[each_student_key][each_exam_key][each_exam_info_key])
                temp_diff_set = all_colname_set - temp_set
                
                for each_col in temp_diff_set:
                    #For all columns that are not found, append None to the remaining lists
                    exam_score_dict[each_col].append(None)

        #Create a data frame from the exam_score_dict
        self.exam_score_df = pd.DataFrame(exam_score_dict)


    def generate_dict_from_score_list(self, list_in):
        """Create a dict with each key being exam score type, e.g. reading, and each value being exam index

        Args:
            list_in (list): list of exam scores

        Returns:
            dict: dict with each key being exam type and each value being exam type index
        """
        num_ind = 1
        dict_out = dict()

        for each_str in list_in:
            dict_out[each_str] = str(num_ind)
            num_ind += 1
        
        return dict_out

    def create_score_and_name_df(self, dict_in, df_orig_in):
        """Create a data frame with all test scores and names from the original data frame and our generated dictionary

        Args:
            dict_in (dict): our generated dictionary of all exam info
            df_orig_in (pd.DataFrame): dataframe of the original exam info

        Returns:
            pd.DataFrame: output data frame of exam information with each column being category 1, 2, and so on
        """
        #Go over all keys in the input dictionary and create new column names
        for each_ind, each_key in enumerate(dict_in.keys()):
            if each_key == 'percentile' or each_key == 'unknown_exam_info':
                temp_column_value = each_key
            else:
                temp_column_value = each_key[:each_key.index('_score')]
            #Each column being either cat_[ind]_name or cat_[ind]_score
            temp_exam_name_colname = 'cat_{}_name'.format(dict_in[each_key])
            temp_exam_score_colname = 'cat_{}_score'.format(dict_in[each_key])
            
            #Create an output dataframe by concatenating these columns together
            temp_df_out = pd.Series([temp_column_value] * df_orig_in.shape[0], index = df_orig_in.index)
            temp_df_out = pd.concat([temp_df_out, df_orig_in[each_key]], axis = 1)
            temp_df_out.columns = [temp_exam_name_colname, temp_exam_score_colname]
            
            #Apply the score type filter to make it more readable
            temp_df_out[temp_exam_name_colname] = temp_df_out[temp_exam_name_colname].apply(self.scoretypefilter)
            
            #Prepare the output data frame
            if each_ind == 0:
                output_df = temp_df_out
            else:
                output_df = pd.concat([output_df, temp_df_out], axis = 1)
        
        return output_df


    def create_output_df(self, df_orig_in, exam_name_colname = 'exam_name', exam_type_colname = 'exam_type', exam_compare_code_colname = 'exam_compare_code', universal_id_colname = 'universal_id', exam_date_colname = 'exam_date'):
        """Create an output data frame for the exam information

        Args:
            df_orig_in (pd.DataFrame): Input data frame of all students having exam information in the column called [exam_name_colname]
            exam_name_colname (str): String of the exam name column
            exam_type_colname (str): String of the exam type column
            exam_compare_code_colname (str): String of the exam comparison column - used as an id for each unique exam
            universal_id_colname (str): String of the column name for universal id
            exam_date_colname (str): String of the exam date column

        Returns:
            pd.DataFrame: An output data frame of all exam information 
        """
        #Find all of the unique exam names
        all_exam_name_array = df_orig_in[exam_name_colname].unique()
        output_df = list()
        
        #Go over all of the exam names in the array
        for each_exam_name in all_exam_name_array:
            #Go over each exam case in an array containing all of the exam names
            temp_df = df_orig_in[df_orig_in[exam_name_colname] == each_exam_name]
            if temp_df.shape[0] > 0:
                #If the exam name exists, use all of the score types of the indicated exam to create the output data frame
                if each_exam_name == 'toefl':
                    all_exam_type_array = temp_df[exam_type_colname].unique()
                    
                    temp_exam_df = list()
                    for each_exam_type in all_exam_type_array:
                        temp_df_sub = temp_df[temp_df[exam_type_colname] == each_exam_type]

                        #Handle the case of TOEFL exam first as some rows would be about TOEFL without saying explicitly
                        if temp_df_sub.shape[0] > 0:
                            assert each_exam_type in {'nan', 'unknown', 'itp', 'ibt'}
                            if each_exam_type == 'unknown' or each_exam_type == 'nan':
                                list_colname_used = self.toefl_overall_score_type_list
                            elif each_exam_type == 'itp':
                                list_colname_used = self.toefl_itp_score_type_list
                            else:
                                list_colname_used = self.toefl_ibt_score_type_list

                            temp_dict_colname = self.generate_dict_from_score_list(list_colname_used)

                            temp_type_df = self.create_score_and_name_df(temp_dict_colname, temp_df_sub)
                            
                            temp_exam_df.append(temp_type_df)
                            
                    temp_exam_df = pd.concat(temp_exam_df, axis=0)
                
                #For each remaining case, create an output data frame for such specific case
                elif each_exam_name == 'sat':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.sat_score_type_list), temp_df)
                
                elif each_exam_name == 'ssat':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.ssat_score_type_list), temp_df)

                elif each_exam_name == 'act':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.act_score_type_list), temp_df)
                    
                elif each_exam_name == 'ielts':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.ietls_score_type_list), temp_df)

                elif each_exam_name == 'psat':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.psat_score_type_list), temp_df)
                
                elif each_exam_name == 'gmat':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.gmat_score_type_list), temp_df)

                elif each_exam_name == 'bmat':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.bmat_score_type_list), temp_df)

                elif each_exam_name == 'gre':
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.gre_score_type_list), temp_df)
                
                else:
                    temp_exam_df = self.create_score_and_name_df(self.generate_dict_from_score_list(self.unknown_score_type_list), temp_df)

                #Go over the data frame and gradually concatenate the data frames altogether
                output_df.append(temp_exam_df)

        #Concatenate all of the rows in the output data frame        
        output_df = pd.concat(output_df, axis=0)
        output_df = pd.concat([df_orig_in[self.output_df_column_order_list], output_df], axis = 1)
        
        #Apply the filters to the output data frames and create a specific column for exam comparison code
        output_df[exam_name_colname] = output_df[exam_name_colname].apply(self.examnamefilter)
        output_df[exam_type_colname] = output_df[exam_type_colname].apply(self.examtypefilter)
        output_df[exam_compare_code_colname] = output_df[universal_id_colname].astype(str) + '_' + output_df[exam_name_colname].astype(str) + '_' + output_df[exam_type_colname].astype(str) + output_df[exam_date_colname].astype(str)

        return output_df


    def process_all(self):
        #Process all of the data to create an output dataframe for showing on the website for each student's column
        self.process_series_in()
        self.create_df_from_series()
        return self.create_output_df(self.exam_score_df)
