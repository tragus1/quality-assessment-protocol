
import scipy.stats as stats


def pass_floats(output_string):
    """Parse AFNI command STDOUT output strings and return the output values 
    as a list of floats.

    :type output_string: str
    :param output_string: An AFNI command standard output.
    :rtype: list
    :return: A list of float values.
    """

    lines = output_string.splitlines()
    values_list = []

    for l in lines:
        try:
            val = float(l)
            values_list.append(val)
        except:
            pass

    return values_list


def calculate_percent_outliers(values_list):
    """Calculate the percentage of outliers from a vector of values.

    :type values_list: list
    :param values_list: A list of float values.
    :rtype: float
    :return: The percentage of values from the input vector that are
             statistical outliers.
    :rtype: float
    :return: The inter-quartile range of the data.
    """

    import numpy as np
    from qap.qap_utils import raise_smart_exception

    try:
        # calculate the IQR
        sorted_values = sorted(values_list)

        third_qr, first_qr = np.percentile(sorted_values, [75, 25])
        IQR = third_qr - first_qr

        # calculate percent outliers
        third_qr_threshold = third_qr + (1.5 * IQR)
        first_qr_threshold = first_qr - (1.5 * IQR)

        high_outliers = \
            [val for val in sorted_values if val > third_qr_threshold]
        low_outliers = \
            [val for val in sorted_values if val < first_qr_threshold]

        total_outliers = high_outliers + low_outliers

        percent_outliers = \
            float(len(total_outliers)) / float(len(sorted_values))

    except:
        raise_smart_exception(locals())

    return percent_outliers, IQR


def fd_jenkinson(in_file, rmax=80., out_file=None, out_array=False):
    """Calculate Jenkinson's Mean Framewise Displacement (aka RMSD) and save 
    the Mean FD values to a file.

    - Method to calculate Framewise Displacement (FD) calculations
      (Jenkinson et al., 2002).
    - Implementation written by @ Krsna, May 2013.
    - Jenkinson FD from 3dvolreg's *.affmat12.1D file from -1Dmatrix_save
      option input: subject ID, rest_number, name of 6 parameter motion
      correction file (an output of 3dvolreg) output: FD_J.1D file
    - in_file should have one 3dvolreg affine matrix in one row - NOT the
      motion parameters.

    :type in_file: str
    :param in_file: Filepath to the coordinate transformation output vector
                    of AFNI's 3dvolreg (generated by running 3dvolreg with
                    the -1Dmatrix_save option).
    :type rmax: float
    :param rmax: (default: 80.0) The default radius of a sphere that
                 represents the brain.
    :type out_file: str
    :param out_file: (default: None) The filepath to where the output file
                     should be written.
    :type out_array: bool
    :param out_array: (default: False) Flag to return the data in a Python
                      NumPy array instead of an output file.
    :rtype: str
    :return: (if out_array=False) The filepath to the output file containing
             the Mean FD values.
    :rtype: NumPy array
    :return: (if out_array=True) An array of the output Mean FD values.
    """

    import numpy as np
    import os.path as op
    from shutil import copyfile
    import math
    from qap.qap_utils import raise_smart_exception

    if out_file is None:
        fname, ext = op.splitext(op.basename(in_file))
        out_file = op.abspath('%s_fdfile%s' % (fname, ext))

    # if in_file (coordinate_transformation) is actually the rel_mean output
    # of the MCFLIRT command, forward that file
    if 'rel.rms' in in_file:
        copyfile(in_file, out_file)
        return out_file

    try:
        pm_ = np.genfromtxt(in_file)
    except:
        raise_smart_exception(locals())

    original_shape = pm_.shape
    pm = np.zeros((pm_.shape[0], pm_.shape[1] + 4))
    pm[:, :original_shape[1]] = pm_
    pm[:, original_shape[1]:] = [0.0, 0.0, 0.0, 1.0]

    # rigid body transformation matrix
    T_rb_prev = np.matrix(np.eye(4))

    flag = 0
    X = [0]  # First timepoint
    for i in range(0, pm.shape[0]):
        # making use of the fact that the order of aff12 matrix is "row-by-row"
        T_rb = np.matrix(pm[i].reshape(4, 4))

        if flag == 0:
            flag = 1
        else:
            M = np.dot(T_rb, T_rb_prev.I) - np.eye(4)
            A = M[0:3, 0:3]
            b = M[0:3, 3]

            FD_J = math.sqrt(
                (rmax * rmax / 5) * np.trace(np.dot(A.T, A)) + np.dot(b.T, b))
            X.append(FD_J)

        T_rb_prev = T_rb

    try:
        np.savetxt(out_file, np.array(X))
    except:
        raise_smart_exception(locals())

    if out_array:
        return np.array(X)
    else:
        return out_file


def outlier_timepoints(func_file, mask_file=None, out_fraction=True):
    """Calculates the number of 'outliers' in a 4D functional dataset, at each
    time-point using AFNI's 3dToutcount.

    - Uses AFNI 3dToutcount. More info here:
        https://afni.nimh.nih.gov/pub/dist/doc/program_help/3dToutcount.html
    - Used for the 'Fraction of Outliers' QAP functional temporal metrics.

    :type func_file: str
    :param func_file: Path to 4D functional timeseries NIFTI file.
    :type mask_file: str
    :param mask_file: Path to the functional binary brain mask NIFTI file.
    :type out_fraction: bool
    :param out_fraction: (default: True) Whether the output should be a count
                         (False) or fraction (True) of the number of masked
                         voxels which are outliers at each time point.
    :rtype: list
    :return: A list of outlier values from AFNI 3dToutcount.
    """

    import commands
    from qap.qap_utils import raise_smart_exception

    opts = []
    if out_fraction:
        opts.append("-fraction")
    if mask_file:
        opts.append("-mask %s" % mask_file)
    opts.append(func_file)
    str_opts = " ".join(opts)

    # TODO:
    # check if should use -polort 2
    # (http://www.na-mic.org/Wiki/images/8/86/FBIRNSupplementalMaterial082005.pdf)
    # or -legendre to remove any trend
    cmd = "3dToutcount %s" % str_opts

    try:
        out = commands.getoutput(cmd)
    except:
        err = "[!] QAP says: Something went wrong with running AFNI's " \
              "3dToutcount."
        raise_smart_exception(locals(),err)

    # remove general information and warnings
    outliers = pass_floats(out)

    return outliers


def quality_timepoints(func_file):
    """Calculates a 'quality index' for each timepoint in the 4D functional
    dataset using AFNI's 3dTqual.

    - Uses AFNI 3dTqual. More info here:
        https://afni.nimh.nih.gov/pub/dist/doc/program_help/3dTqual.html
    - Used for the 'Quality' QAP functional temporal metrics.
    - Low values are good and indicate that the timepoint is not very
      different from the norm.

    :type func_file: str
    :param func_file: Filepath to the 4D functional timerseries NIFTI file.
    :rtype: list
    :return: A list of float values from AFNI 3dTqual.
    """

    import subprocess
    from qap.qap_utils import raise_smart_exception

    opts = []
    opts.append(func_file)
    str_opts = " ".join(opts)

    cmd = "3dTqual %s" % str_opts

    try:
        p = subprocess.Popen(cmd.split(" "),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
    except:
        err = "[!] QAP says: Something went wrong with running AFNI's " \
              "3dTqual."
        raise_smart_exception(locals(),err)

    quality = pass_floats(out)

    return quality


def global_correlation(func_reorient, func_mask):
    """Calculate the global correlation (GCOR) of the functional timeseries.

    - From "Correcting Brain-Wide Correlation Differences in Resting-State
      fMRI", Ziad S. Saad et al. More info here:
        https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3749702

    :type func_reorient: str
    :param func_reorient: Filepath to the deobliqued, reoriented functional
                          timeseries NIFTI file.
    :type func_mask: str
    :param func_mask: Filepath to the functional brain mask NIFTI file.
    :rtype: float
    :return: The global correlation (GCOR) value.
    """

    import scipy
    import numpy as np
    from dvars import load

    zero_variance_func = load(func_reorient, func_mask)

    list_of_ts = zero_variance_func.transpose()

    # get array of z-scored values of each voxel in each volume of the
    # timeseries
    demeaned_normed = []

    for ts in list_of_ts:
        demeaned_normed.append(scipy.stats.mstats.zscore(ts))

    demeaned_normed = np.asarray(demeaned_normed)

    # make an average of the normalized timeseries, into one averaged
    # timeseries, a vector of N volumes
    volume_list = demeaned_normed.transpose()

    avg_ts = []

    for voxel in volume_list:
        avg_ts.append(voxel.mean())

    avg_ts = np.asarray(avg_ts)

    # calculate the global correlation
    gcor = (avg_ts.transpose().dot(avg_ts)) / len(avg_ts)

    return gcor


def calc_temporal_std(voxel_ts):

    import numpy as np

    voxel_std = np.std(voxel_ts)

    return voxel_std


def get_temporal_std_map(func_reorient, func_mask):

    import numpy as np
    from qap.qap_utils import get_masked_data

    func_data = get_masked_data(func_reorient, func_mask)

    temporal_std_map = np.zeros(func_data.shape[0:3])

    for i in range(0, len(func_data)):
        for j in range(0, len(func_data[0])):
            for k in range(0, len(func_data[0][0])):
                std = np.std(func_data[i][j][k])
                temporal_std_map[i][j][k] = std

    return temporal_std_map


def create_threshold_mask(data, threshold):

    import numpy as np

    mask = np.zeros(data.shape)

    for i in range(0, len(data)):
        for j in range(0, len(data[0])):
            for k in range(0, len(data[0][0])):
                if data[i][j][k] > threshold:
                    mask[i][j][k] = 1
                else:
                    mask[i][j][k] = 0

    return mask


def calc_estimated_csf_nuisance(temporal_std_map):

    import numpy as np
    from qap.qap_utils import get_masked_data

    all_tstd = np.asarray(temporal_std_map.nonzero()).flatten()
    all_tstd_sorted = sorted(all_tstd)
    top_2 = 0.98 * len(all_tstd)

    top_2_std = all_tstd_sorted[int(top_2):]
    cutoff = top_2_std[0]

    estimated_nuisance_mask = create_threshold_mask(temporal_std_map, cutoff)

    nuisance_stds = get_masked_data(temporal_std_map, estimated_nuisance_mask)

    nuisance_mean_std = np.mean(np.asarray(nuisance_stds.nonzero()).flatten())

    return nuisance_mean_std


def sfs_voxel(voxel_ts, total_func_mean, nuisance_mean_std):
    """Calculate the Signal Fluctuation Intensity (SFS) of one voxel's
    functional time series.

    - From "Signal Fluctuation Sensitivity: An Improved Metric for Optimizing
      Detection of Resting-State fMRI Networks", Daniel J. DeDora1,
      Sanja Nedic, Pratha Katti, Shafique Arnab, Lawrence L. Wald, Atsushi
      Takahashi, Koene R. A. Van Dijk, Helmut H. Strey and
      Lilianne R. Mujica-Parodi. More info here:
        http://journal.frontiersin.org/article/10.3389/fnins.2016.00180/full

    :rtype: NumPy array
    :return: The signal fluctuation intensity timecourse for the voxel
             timeseries provided.
    """

    import numpy as np

    voxel_ts_mean = np.mean(voxel_ts)
    voxel_ts_std = np.std(voxel_ts)

    sfs_vox = \
        (voxel_ts_mean/total_func_mean) * (voxel_ts_std/nuisance_mean_std)

    return sfs_vox


def sfs_timeseries(func_mean, func_mask, temporal_std_map):
    """Average the SFS timecourses of each voxel into one SFS timeseries.

    :rtype: NumPy array
    :return: The averaged signal fluctuation intensity timeseries for the
             entire brain.
    """

    import numpy as np
    import nibabel as nb

    func_mean_img = nb.load(func_mean)
    func_mean_data = func_mean_img.get_data()
    func_mask_img = nb.load(func_mask)
    func_mask_data = func_mask_img.get_data()

    masked_func_mean = func_mean_data[func_mask_data.nonzero()]
    total_func_mean = np.mean(masked_func_mean)

    masked_tstd = temporal_std_map[func_mask_data.nonzero()]

    nuisance_mean_std = calc_estimated_csf_nuisance(temporal_std_map)

    arg_tuples = []
    for voxel_ts, voxel_std in zip(masked_func_mean, masked_tstd):
        arg_tuples.append(voxel_ts, total_func_mean, voxel_std,
                          nuisance_mean_std)

    sfs_voxels = map(sfs_voxel, arg_tuples)

    return sfs_voxels



