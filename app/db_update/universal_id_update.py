import requests
import json

base_url = "https://www.streak.com/api/v1/"
pipeline = 'agxzfm1haWxmb29nYWVyOAsSDE9yZ2FuaXphdGlvbiIRcmFwaXNhdEBnbWFpbC5jb20MCxIIV29ya2Zsb3cYgICAgICumQoM'
auth = 'a29b8cff6bc944ee8b409c00b4ef8a4d'

class update_streak_data:
    """
    Update the data from Streak using information from our data frame
    """
    def __init__(self, base_streak_url, auth_key, target_pipeline_key):
        """Initialize the class for updating Streak data

        Args:
            base_streak_url (str): Streak URL for updating the information
            auth_key (str): String of the authentication key
            target_pipeline_key (str): String of the pipeline key
        """
        self.base_streak_url = base_streak_url
        self.auth_key = auth_key
        self.target_pipeline_key = target_pipeline_key
        self.student_boxes = None #Student boxes
        self.pipeline = None #Pipeline object
        self.id_added_num = 0 #Number of boxes to have ids added

    def retrieve_student_boxes(self):
        """
        Retrieve student boxes from Streak using the given URL 
        """
        student_box_url = self.base_streak_url + "pipelines/" + self.target_pipeline_key + "/boxes"
        headers = {'content-type': 'application/json'}

        #Load the student boxes from the request
        response = requests.request("GET", student_box_url, headers=headers, auth = (self.auth_key,''))
        self.student_boxes = json.loads(response.text)

    def add_field_and_find_field_key(self, target_field_name):
        """Add a field in Streak and find the field's key 

        Args:
            target_field_name (str): Name of the new field 

        Returns:
            str: Key of the new field
        """
        pipeline_field_url = self.base_streak_url + "pipelines/" + self.target_pipeline_key + '/fields'

        payload = "name={}&type=TEXT_INPUT".format(target_field_name)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.request("PUT", pipeline_field_url, data=payload, headers=headers)

        return json.loads(response.text)['key']

    def find_field_key(self, target_field_name):
        """Find the field key with the field name matching with our input field name. If the field doesn't exist, add the new field matching the target field name

        Args:
            target_field_name (str): field name to be matched with

        Returns:
            str: field key of the target column
        """
        pipeline_url = self.base_streak_url + "pipelines/" + self.target_pipeline_key
        headers = {'content-type': 'application/json'}

        response = requests.request("GET", pipeline_url, headers=headers, auth = (self.auth_key,''))
        self.pipeline = json.loads(response.text)

        #Go over all fields in the pipeline and find such field
        for each_dict in self.pipeline['fields']:
            if each_dict['name'] == target_field_name:
                return each_dict['key']
        
        return self.add_field_and_find_field_key(target_field_name)
            
    def update_box_val(self, box_key, field_key, value):
        """Update a box value targeted

        Args:
            box_key (str): Target box key
            field_key (str): Target field key
            value (str): Value to be updated into the box
        """
        url = self.base_streak_url + "boxes/" + box_key + "/fields/" + field_key

        payload = {"value": value}
        headers = {"Content-Type": "application/json"}

        response = requests.request("POST", url, json=payload, headers=headers, auth = (self.auth_key,''))

        print(response.text)
        
    def find_pipeline_max_id(self, field_key):
        """Find the max id for the given field - used for adding new universal ids

        Args:
            field_key (str): string of the field key

        Returns:
            int: value of the max integer value in the target field
        """
        current_max_id = 0
        for each_box in self.student_boxes:
            if field_key in each_box['fields']:
                if each_box['fields'][field_key] != '':
                    if int(each_box['fields'][field_key]) > current_max_id:
                        current_max_id = int(each_box['fields'][field_key])
        return current_max_id

    def create_universal_id_all(self, field_key, max_id_other_pipeline = None):
        """Create universal ids for all new boxes in target field

        Args:
            field_key (str): key of the targeted field
            max_id_other_pipeline ([type], optional): [description]. Defaults to None.
        """
        #Go over all of the boxes and find the boxes with missing values
        current_max_id = 0
        box_key_missing_id_list = list()
        for each_box in self.student_boxes:
            if field_key in each_box['fields']:
                if each_box['fields'][field_key] != '':
                    if int(each_box['fields'][field_key]) > current_max_id:
                        current_max_id = int(each_box['fields'][field_key])
                else:
                    box_key_missing_id_list.append(each_box['boxKey'])
            else:
                box_key_missing_id_list.append(each_box['boxKey'])
        
        #If the other pipeline has a greater max id, we will use the max id from the other pipeline
        if max_id_other_pipeline is not None:
            if max_id_other_pipeline > current_max_id:
                current_max_id = max_id_other_pipeline
        
        #Increment the id and update each box with the id value
        for each_box_key in box_key_missing_id_list:
            self.update_box_val(each_box_key, field_key, current_max_id + 1)
            current_max_id += 1
        
        self.id_added_num = len(box_key_missing_id_list)

    def run_main(self, target_field_name, max_id_other_pipeline=None):
        """Retrieve all student boxes, find the field key of the universal_id field, and create universal ids for all of the boxes with missing ids

        Args:
            target_field_name (str): name of the target field
            max_id_other_pipeline (int, optional): value of the max id from the other pipeline. Defaults to None.
        """
        if self.student_boxes is not None:
            self.retrieve_student_boxes()
        target_field_key = self.find_field_key(target_field_name)
        self.create_universal_id_all(target_field_key, max_id_other_pipeline)