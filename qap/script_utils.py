
def read_txt_file(txt_file):
    """Read in a text file into a list of strings.

    :type txt_file: str
    :param txt_file: Filepath to the text file.
    :rtype: list
    :return: A list of strings, the lines in the text file.

    """

    with open(txt_file,"r") as f:
        strings = f.read().splitlines()
    return strings


def read_yml_file(yml_file):
    """Read in a YAML file into a dictionary.

    :type yml_file: str
    :param yml_file: Filepath to the YAML file.
    :rtype: dict
    :return: Dictionary of the data stored in the YAML
    """

    import os
    import yaml
    with open(os.path.realpath(yml_file), "r") as f:
        config = yaml.load(f)
    return config


def gather_filepath_list(site_folder):
    """Gather all of the NIFTI files under a provided directory.

    :type site_folder: str
    :param site_folder: Path to the base directory containing all of the
                        NIFTI files you wish to gather.
    :rtype: list
    :return: A list of filepaths to the NIFTI files found within and under
             the provided site folder.
    """

    import os

    site_folder = os.path.abspath(site_folder)

    filepath_list = []
    for root, folders, files in os.walk(site_folder):
        for filename in files:
            fullpath = os.path.join(root, filename)
            if ".nii" in fullpath:
                filepath_list.append(fullpath)

    return filepath_list


def csv_to_pandas_df(csv_file):
    """Convert the data in a CSV file into a Pandas DataFrame.

    :type csv_file: str
    :param csv_file: The filepath to the CSV file to be loaded.
    :rtype: Pandas DataFrame
    :return: A DataFrame object with the data from the CSV file.
    """

    import pandas as pd
    from qap.workflow_utils import raise_smart_exception

    try:
        data = pd.read_csv(csv_file)
    except Exception as e:
        err = "Could not load the CSV file into a DataFrame using Pandas." \
              "\n\nCSV file: %s\n\nError details: %s\n\n" % (csv_file, e)
        raise_smart_exception(locals(),err)

    return data


def parse_raw_data_list(filepath_list, site_folder, inclusion_list=None,
                        s3_bucket=False):
    """Parse a list of NIFTI filepaths into a participant data dictionary for
    the 'qap_raw_data_sublist_generator.py' script.

    - This is for the 'qap_sublist_generator.py' script.
    - This is designed for data directories formatted as such:
        /site_folder/participant_ID/session_ID/scan_ID/filename.nii.gz

    :type filepath_list: str
    :param filepath_list: A list of input file NIFTI filepaths.
    :type site_folder: str
    :param site_folder: The root directory containing the NIFTI filepaths in
                        the list.
    :type inclusion_list: list
    :param inclusion_list: (default: None) A list of participant IDs to
                           include in the sublist dictionary.
    :type s3_bucket: bool
    :param s3_bucket: A flag denoting whether the list contains AWS S3 bucket
                      filepaths instead of local disk filepaths.
    :rtype: dict
    :return: A dictionary containing the NIFTI files indexed by participant
             information.
    """

    import os

    sub_dict = {}
    if not inclusion_list:
        inclusion_list = []
        inclusion = False

    if not s3_bucket:
        site_folder = os.path.abspath(site_folder)
    
    for fullpath in filepath_list:
            
        # /path_to_site_folder/subject_id/session_id/scan_id/..
        try:
            second_half = fullpath.split(site_folder)[1]
        except:
            err = "[!] Something went wrong with the filepath " \
                  "parsing.\n\nFilepath: %s\nSite folder: %s\n" \
                  % (fullpath, site_folder)
            raise Exception(err)
        second_half_list = second_half.split("/")
        filename = second_half_list[-1]

        try:
            second_half_list.remove("")
        except:
            pass

        try:
            site_id = second_half_list[-5]
            subject_id = second_half_list[-4]
            session_id = second_half_list[-3]
            scan_id = second_half_list[-2]
        except:
            err = "\n\n[!] Could not parse the data directory " \
                  "structure for this file - is it in the " \
                  "correct format?\nFile path:\n%s\n\nIt should "\
                  "be something like this:\n/site_folder/subject"\
                  "_id/session_id/scan_id/file.nii.gz\n\n" \
                  % second_half
            print err

        if not inclusion:
            inclusion_list.append(subject_id)

        resource = None

        if ("anat" in scan_id) or ("anat" in filename) or \
            ("mprage" in filename):
            resource = "anatomical_scan"
            
        if ("rest" in scan_id) or ("rest" in filename) or \
            ("func" in scan_id) or ("func" in filename):
            resource = "functional_scan"

        if (resource == "anatomical_scan") and \
                (subject_id in inclusion_list):

            if subject_id not in sub_dict.keys():
                sub_dict[subject_id] = {}
            
            if session_id not in sub_dict[subject_id].keys():
                sub_dict[subject_id][session_id] = {}
            
            if resource not in sub_dict[subject_id][session_id].keys():
                sub_dict[subject_id][session_id][resource] = {}
                sub_dict[subject_id][session_id]["site_name"] = site_id
                                               
            if scan_id not in sub_dict[subject_id][session_id][resource].keys():
                sub_dict[subject_id][session_id][resource][scan_id] = fullpath
                
        if (resource == "functional_scan") and \
                 (subject_id in inclusion_list):

            if subject_id not in sub_dict.keys():
                sub_dict[subject_id] = {}
            
            if session_id not in sub_dict[subject_id].keys():
                sub_dict[subject_id][session_id] = {}
            
            if resource not in sub_dict[subject_id][session_id].keys():
                sub_dict[subject_id][session_id][resource] = {}
                sub_dict[subject_id][session_id]["site_name"] = site_id
                            
            if scan_id not in sub_dict[subject_id][session_id][resource].keys():
                sub_dict[subject_id][session_id][resource][scan_id] = fullpath

    if len(sub_dict) == 0:
        err = "\nThe participant list came out empty! Double-check your " \
              "settings.\n"
        raise Exception(err)

    return sub_dict


def populate_custom_data_dict(data_dict, filepath, part_id, session_id, series_id,
    site_id, resource, default_series_label=None):
    """Update a participant data dictionary with a NIFTI filepath keyed to
    a participant's information, for the 'gather_custom_raw_data.py' script.

    Keyword Arguments:
      data_dict -- [Python dictionary] the participant data dictionary
      filepath -- [string] the new NIFTI filepath to add to the dictionary
      part_id -- [string] the participant ID
      session_id -- [string] the session ID
      series_id -- [string] the series/scan ID
      site_id -- [string] the site name/ID
      resource -- [string] the name of the type of data/file the NIFTI file is
      default_series_label -- [string] (default: None) a default to use for 
                              series/scan names/IDs

    Returns:
      data_dict -- [Python dictionary] the updated version of the data_dict 
                   provided in the inputs

    Notes:
      - This is for the 'gather_custom_raw_data.py' script, but is called in
        the 'gather_custom_raw_data' function, one NIFTI file at a time.
    """

    new_dict = data_dict

    if not session_id:
        session_id = "session_1"
    if not series_id:
        if default_series_label:
            series_id = default_series_label
        else:
            series_id = "scan_1"

    if part_id not in new_dict.keys():
        new_dict[part_id] = {}
    if session_id not in new_dict[part_id].keys():
        new_dict[part_id][session_id] = {}
    if resource not in new_dict[part_id][session_id].keys():
        new_dict[part_id][session_id][resource] = {}
    if site_id not in new_dict[part_id][session_id].keys():
        new_dict[part_id][session_id]["site_name"] = site_id
    if series_id not in new_dict[part_id][session_id][resource].keys():
        new_dict[part_id][session_id][resource][series_id] = filepath    

    data_dict.update(new_dict)

    return data_dict


def gather_custom_raw_data(filepath_list, base_folder, directory_format, 
    anatomical_keywords=None, functional_keywords=None):
    """Parse a list of NIFTI filepaths into a participant data dictionary 
    when the NIFTI filepaths are based on a custom data directory format, for
    the 'qap_flexible_sublist_generator.py' script.

    Keyword Arguments:
      filepath_list -- [Python list] a list of NIFTI filepaths
      base_folder -- [string] the root directory containing all of the NIFTI 
                     filepaths in the list
      directory_format -- [string] a string describing the data directory 
                          layout in the format '/{site}/{participant}/..'
                          '..{session}/..' etc. where the order of the {} 
                          items can vary
      anatomical_keywords -- [string] (default: None) a string of space- 
                             delimited keywords that may be in the NIFTI 
                             filepath or filename that denotes the file is 
                             anatomical
      functional_keywords -- [string] (default: None) a string of space-
                             delimited keywords that may be in the NIFTI 
                             filepath or filename that denotes the file is 
                             functional

    Returns:
      data_dict -- [Python dictionary] the participant data dictionary

    Notes:
      - This is for the 'qap_flexible_sublist_generator.py' script.
      - This is to facilitate participant dictionary generation for data 
        directory formats that are neither BIDS-format nor conventional 
        (/site/participant/session/scan/file).
    """

    import os
    from qap.script_utils import populate_custom_data_dict

    if "{participant}" not in directory_format:
        pass

    data_dict = {}

    base_folder = os.path.abspath(base_folder)
    format_list = [x for x in directory_format.split("/") if x != ""]

    indices = {}
    operators = ["{site}", "{participant}", "{session}", "{series}"]

    for op in operators:
        if op in format_list:
            indices[op] = format_list.index(op)

    if anatomical_keywords:
        anatomical_keywords = [x for x in anatomical_keywords.split(" ") if x != ""]

    if functional_keywords:
        functional_keywords = [x for x in functional_keywords.split(" ") if x != ""]

    for filepath in filepath_list:

        second_half_list = [x for x in filepath.split(base_folder)[1].split("/") if x != ""]
        filename = second_half_list[-1]

        site_id = None
        part_id = None
        session_id = None
        series_id = None

        if "{site}" in indices.keys():
            site_id = second_half_list[indices["{site}"]]
        if "{participant}" in indices.keys():
            part_id = second_half_list[indices["{participant}"]]
        if "{session}" in indices.keys():
            session_id = second_half_list[indices["{session}"]]
        if "{series}" in indices.keys():
            series_id = second_half_list[indices["{series}"]]

        if anatomical_keywords:
            for word in anatomical_keywords:
                if (word in filename) or (word in session_id):

                    data_dict = populate_custom_data_dict(data_dict,
                                                   filepath, part_id,
                                                   session_id,
                                                   series_id,
                                                   site_id,
                                                   "anatomical_scan",
                                                   "anat_1")

        if functional_keywords:
            for word in functional_keywords:
                if (word in filename) or (word in session_id):

                    data_dict = populate_custom_data_dict(data_dict,
                                                   filepath, part_id,
                                                   session_id,
                                                   series_id,
                                                   site_id,
                                                   "functional_scan",
                                                   "func_1")

    if len(data_dict) == 0:
        err = "\n\n[!] No data files were found given the inputs you " \
              "provided! Double-check your setup.\n\n"
        raise Exception(err)

    return data_dict


def pull_s3_sublist(bucket_name, bucket_prefix, creds_path=None):
    """Create a list of filepaths stored on the Amazon S3 bucket.

    Keyword Arguments:
      bucket_name -- [string] the name of the Amazon S3 bucket
      bucket_prefix -- [string] the directory path of the root directory of
                       your data on the S3 bucket
      creds_path -- [string] the filepath to your Amazon AWS keys

    Returns:
      s3_list -- [Python list] a list of Amazon S3 filepaths from the bucket
                 and bucket directory you provided
    """

    import os
    from indi_aws import fetch_creds

    if creds_path:
        creds_path = os.path.abspath(creds_path)

    s3_list = []
    bucket = fetch_creds.return_bucket(creds_path, bucket_name)

    # ensure slash at end of bucket_prefix, so that if the final
    # directory name is a substring in other directory names, these
    # other directories will not be pulled into the file list
    if "/" not in bucket_prefix[-1]:
        bucket_prefix += "/"

    # Build S3-subjects to download
    for bk in bucket.objects.filter(Prefix=bucket_prefix):
        s3_list.append("/".join(["s3:/", bucket_name, str(bk.key)]))

    return s3_list


def gather_json_info(output_dir):
    """Extract the dictionaries from the JSON output files and merge them into
    one dictionary.

    Parameters: ::
      output_dir : [string]
        the path to the main output directory of the QAP run

    Returns: ::
      json_dict : [dictionary]
        the output data of the QAP run keyed by participant-session-scan
    """

    import os
    from qap.qap_workflows_utils import read_json

    json_dict = {}

    for root, dirs, files in os.walk(os.path.abspath(output_dir)):
        for filename in files:
            if ".json" in filename:
                filepath = os.path.join(root,filename)
                temp_dict = read_json(filepath)
                json_dict.update(temp_dict)

    return json_dict

    
def json_to_csv(json_dict, csv_output_dir=None):
    """Extract the data from the JSON output file and write it to a CSV file.

    Keyword arguments:
      json_dict -- [dictionary] dictionary containing all of the JSON output
                   information from the QAP run
      csv_output_dir -- [string] (default: None) path to the directory to 
                        write the CSV file into

    Returns:
      csv_file -- [string] the CSV file path
    """

    import os
    import simplejson
    import pandas as pd
    from qap.workflow_utils import raise_smart_exception

    qap_types = ["anatomical_spatial",
                 "functional_spatial",
                 "functional_temporal"]

    output_dict = {}

    for sub_sess_scan in json_dict.keys():
        # flatten the JSON dict
        sub_json_dict = json_dict[sub_sess_scan]
        header_dict = {}
        qap_dict = {}

        try:
            header_dict = sub_json_dict["anatomical_header_info"]
        except KeyError:
            pass

        try:
            header_dict = sub_json_dict["functional_header_info"]
        except KeyError:
            pass

        for qap_type in qap_types:
            try:
                qap_dict = sub_json_dict[qap_type]
            except KeyError:
                continue

            for key in sub_json_dict.keys():
                if "anatomical" not in key and "functional" not in key:
                    qap_dict[key] = sub_json_dict[key]

            qap_dict.update(header_dict)

            try:
                output_dict[qap_type].append(qap_dict)
            except KeyError:
                output_dict[qap_type] = [qap_dict]

    for qap_type in output_dict.keys():

        json_df = pd.DataFrame(output_dict[qap_type])
        json_df.sort_values(by=["Participant","Session","Series"],
                            inplace=True)
        if not csv_output_dir:
            csv_output_dir = os.getcwd()
        csv_file = os.path.join(csv_output_dir, "qap_%s.csv" % qap_type)

        try:
            json_df.to_csv(csv_file)
        except:
            err = "Could not write CSV file!\nCSV file: %s" % csv_file
            raise_smart_exception(locals(),err)

    return csv_file


def create_CPAC_outputs_dict(cpac_outdir, qap_type, session_format):

    # for script 'qap_cpac_output_sublist_generator.py'

    ''' WARNING: OUT OF DATE!!! '''

    import os
    import glob

    cpac_outdir = os.path.abspath(cpac_outdir)

    if qap_type == "anat":

        outputs = ["anatomical_reorient", "anatomical_csf_mask", \
                   "anatomical_gm_mask", "anatomical_wm_mask", \
                   "anatomical_to_mni_linear_xfm"]

    elif qap_type == "func":

        outputs = ["mean_functional", "functional_brain_mask", \
                   "raw_functional", "coordinate_transformation"]

    outputs_dict = {}

    for sub_dir in os.listdir(cpac_outdir):

        if not os.path.isdir(os.path.join(cpac_outdir, sub_dir)):
            continue

        sessions = []

        # if the folder structure is sub_id/session_id/scan_id/...
        if session_format == 1:
            for session in os.listdir(os.path.join(cpac_outdir, sub_dir)):
                if os.path.isdir(os.path.join(cpac_outdir, sub_dir, session)):
                    sessions.append(session)

        # if there is no session label in the folder structure
        if session_format == 2:
            # since there is no session, let's assign one
            sessions = ["session_1"]

        # if the session is embedded in the subject ID
        if session_format == 3:
            subject_session = sub_dir

            if "_" not in sub_dir:
                err = "\n\n[!] You said your CPAC output directory had the " \
                      "session IDs embedded in the subject IDs, but it " \
                      "doesn't seem that way for subject ID %s!\n\nIs it " \
                      " formatted like this?   ../pipeline_output/subject_" \
                      "session/output/..\n\nIf not, you're using the wrong " \
                      "option for session_format! Use the -h flag to see " \
                      "the documentation.\n\n%s not being included in the " \
                      "subject list.\n\n" % (sub_dir, sub_dir)
                print err
                continue

            session_id = sub_dir.split("_",1)[1]
            sub_dir = sub_dir.split("_",1)[0]
            sessions = [session_id]

        for session in sessions:

            for resource in outputs:

                resource_path = ""

                if session_format == 1:
                    resource_folder = os.path.join(cpac_outdir, sub_dir, \
                                                       session, resource)
                elif session_format == 2:
                    resource_folder = os.path.join(cpac_outdir, sub_dir, \
                                                       resource)

                elif session_format == 3:
                    resource_folder = os.path.join(cpac_outdir, \
                                                       subject_session, \
                                                       resource)

                # if this current resource/output does not exist for this
                # subject, go to next resource in list
                if not os.path.isdir(resource_folder):
                    continue

                if qap_type == "anat":

                    ''' until CPAC writes multiple anat scans in the '''
                    ''' output folder structure '''
                    scans = ["anat_1"]

                if qap_type == "func":
    
                    scans = []

                    for item in os.listdir(resource_folder):
                        if os.path.isdir(os.path.join(resource_folder, item)):
                            item = item.replace("_scan_","")
                            item = item.replace("_rest","")
                            scans.append(item)

                for scan in scans:

                    if qap_type == "anat":

                        if "mask" in resource:
                            resource_paths = glob.glob(os.path.join(resource_folder, "*", "*"))
                        else:
                            resource_paths = glob.glob(os.path.join(resource_folder, "*"))

                        if len(resource_paths) == 1:
                            resource_path = resource_paths[0]
                        else:
                            print "\nMultiple files for %s for subject %s!!" \
                                  % (resource, sub_dir)
                            print "Check the directory: %s" \
                                      % resource_folder
                            print "%s for %s has not been included in the " \
                                  "subject list.\n" % (resource, sub_dir)
                            continue

                    if qap_type == "func":

                        fullscan = "_".join(["_scan", scan, "rest"])

                        resource_paths = glob.glob(os.path.join(resource_folder, fullscan, "*"))

                        if len(resource_paths) == 1:
                            resource_path = resource_paths[0]
                        else:
                            print "\nMultiple files for %s for subject %s!!" \
                                  % (resource, sub_dir)
                            print "Check the directory: %s" \
                                      % resource_folder
                            print "%s for %s has not been included in the " \
                                  "subject list.\n" % (resource, sub_dir)
                            continue

                    ''' put a catch here for multiple files '''

                    if sub_dir not in outputs_dict.keys():
                        outputs_dict[sub_dir] = {}

                    if session not in outputs_dict[sub_dir].keys():
                        outputs_dict[sub_dir][session] = {}

                    if resource not in outputs_dict[sub_dir][session].keys():
                        outputs_dict[sub_dir][session][resource] = {}

                    if scan not in outputs_dict[sub_dir][session][resource].keys():
                        outputs_dict[sub_dir][session][resource][scan] = resource_path

    # make up for QAP - CPAC resource naming discrepancy
    for subid in outputs_dict.keys():

        for session in outputs_dict[subid].keys():

            for resource in outputs_dict[subid][session].keys():

                if resource == "motion_correct":

                    filepath = outputs_dict[subid][session]["motion_correct"]

                    outputs_dict[subid][session]["func_motion_correct"] = \
                        filepath

                    del outputs_dict[subid][session]["motion_correct"]

                if resource == "anatomical_to_mni_linear_xfm":

                    filepath = outputs_dict[subid][session]["anatomical_to_mni_linear_xfm"]

                    outputs_dict[subid][session]["flirt_affine_xfm"] = \
                        filepath

                    del outputs_dict[subid][session]["anatomical_to_mni_linear_xfm"]

    return outputs_dict


def qap_csv_correlations(data_old, data_new, replacements=None):
    """Create a dictionary of correlations between old and new versions of 
    each QAP measure for the purpose of regression testing, for the 
    'qap_test_correlations.py' script.

    Keyword Arguments:
      data_old -- [Pandas DataFrame] a dataframe of QAP output measures from
                  the older-version run
      data_new -- [Pandas DataFrame] a dataframe of QAP output measures from
                  the newer-version run
      replacements -- [Python list] a list of strings describing column name
                      replacements, in case column names have changed; these
                      strings are in the format "old_name,new_name"

    Returns:
      correlations_dict -- [Python dictionary] a dictionary of correlations 
                           values keyed by each QAP metric

    Notes:
      - This is for the 'qap_test_correlations.py' script.
      - This is intended for regression testing between versions of the QAP
        software.
      - The 'metric_list' below must be kept current with changes to metrics
        and their titles.
    """

    import numpy as np
    import pandas as pd
    import scipy.stats

    metric_list = ["EFC","SNR","FBER","CNR","FWHM","Qi1","Cortical Contrast",
        "Ghost_x", "Ghost_y", "Ghost_z", "GCOR", "RMSD (Mean)", 
        "Quality (Mean)", "Fraction of Outliers (Mean)", "Std. DVARS (Mean)", 
        "Fraction of OOB Outliers (Mean)"]

    # update datasets if necessary
    if replacements:
        replace_dict = {}
        for word_couple in replacements:
            if "," not in word_couple:
                err = "\n\n[!] In the replacements text file, the old " \
                      "substring and its replacement must be separated " \
                      "by a comma.\n\nLine: %s\n\n" % word_couple
                raise Exception(err)
            word = word_couple.split(",")[0]
            new = word_couple.split(",")[1]
            replace_dict[word] = new

        data_old.rename(columns=replace_dict, inplace=True)
        data_new.rename(columns=replace_dict, inplace=True)

    # remove nulls
    data_old = data_old[pd.notnull(data_old["Participant"])]
    data_new = data_new[pd.notnull(data_new["Participant"])]

    for metric in metric_list:
        if metric in data_old:
            data_old = data_old[pd.notnull(data_old[metric])]
        if metric in data_new:
            data_new = data_new[pd.notnull(data_new[metric])]

    # make sure participant IDs are strings (if they are all digits, can be
    # mistakenly read in as ints or floats)
    if data_old["Participant"].dtype != str:
        data_old["Participant"] = data_old["Participant"].astype(int).astype(str)

    if data_new["Participant"].dtype != str:
        data_new["Participant"] = data_new["Participant"].astype(int).astype(str)

    # make sure both DFs match
    data_merged = pd.merge(data_old, data_new, 
        on=["Participant","Session","Series"], how="inner", 
        suffixes=("_OLD","_NEW"))

    # correlate the numbers!
    correlations_dict = {}
    for metric in metric_list:
        metric_old = "_".join([metric, "OLD"])
        metric_new = "_".join([metric, "NEW"])
        if (metric_old in data_merged) and (metric_new in data_merged):
            metric_old_val = data_merged[metric_old]#.flatten()
            metric_new_val = data_merged[metric_new]#.flatten()
            correlations_dict[metric] = scipy.stats.pearsonr(metric_old_val, metric_new_val)

    return correlations_dict


def write_inputs_dict_to_yaml_file(input_dict, yaml_outpath):
    """Write a participant data dictionary to a YAML file.

    Keyword Arguments:
      input_dict -- [Python dictionary] a participant data dictionary keyed by
                    participant information
      yaml_outpath -- [string] the filepath where to write the YAML file to

    Returns:
      N/A

    Notes:
      - This is used across the participant list generator scripts.
      - yaml_outpath should also include the YAML filename.
    """

    import os
    import yaml         

    yaml_outpath = os.path.abspath(yaml_outpath)
    if (".yml" not in yaml_outpath) and (".yaml" not in yaml_outpath):
        yaml_outpath += ".yml"

    # write yaml file
    try:
        with open(yaml_outpath,"wt") as f:
            f.write(yaml.dump(input_dict, default_flow_style=True))
    except:
        err = "\n\n[!] Error writing YAML file output.\n1. Do you have " \
              "write permissions for the output path provided?\n2. Did you " \
              "provide a full path for the output path? Example: /home/data" \
              "/sublist.yml\n\nOutput path provided: %s\n\n" % yaml_outpath
        raise Exception(err)
        
    if os.path.isfile(yaml_outpath):
        print "\nInputs dictionary file successfully created: %s\n" \
              % yaml_outpath
    else:
        err = "\n[!] Filepaths from the have not been successfully " \
              "saved to the YAML file!\nOutput filepath: %s\n" \
              % yaml_outpath
        raise Exception(err)
