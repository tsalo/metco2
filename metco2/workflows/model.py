import nipype.interfaces.io as nio
import nipype.pipeline.engine as pe
from niworkflows.nipype.interfaces import utility as niu
from nipype.interfaces.afni.model import (Deconvolve, Synthesize)


def init_metco2_wf(images, events, confounds, subject_id, out_dir):
    """
    This workflow ... .

    .. workflow::
    :graph2use: orig
    :simple_form: yes

       from metco2.workflows.base import init_metco2_wf
       wf = init_metco2_wf(subject='fmripreptest')

    Parameters
    ------
    Confounds
        Filname
    Events
        List of filenames
    Images
        4D NIfTI image
    """
    metco2_wf = pe.Workflow(name='metco2_wf')

    # input node for gathering relevant files
    inputnode = pe.Node(niu.IdentityInterface(fields=['subject_id',
                                                      'images',
                                                      'events']),
                        name='inputnode')

    gen_stims = pe.Node(niu.Function(input_names=['event_list'],
                                     output_names=['stim_tuples'],
                                     function=_gen_stim_list),
                        name='gen_stims')

    # run a GLM in AFNI using 3dDeconvolve
    deconvolve = pe.Node(Deconvolve(),
                         name='deconvolve')
    deconvolve.inputs.ortvec = (confounds, 'confounds')
    deconvolve.inputs.x1D = 'matrix.1D'
    deconvolve.inputs.cbucket = 'cbucket'

    # use 3dSynthesize to remove the variance associated with
    # our physiological confounds
    syn = pe.Node(Synthesize(outputtype='NIFTI_GZ'), name='synthesize')
    syn.inputs.select = ['baseline', 'polort', 'allfunc']

    # save out the corrected data to a datasink
    datasink = pe.Node(nio.DataSink(), name='datasink')
    datasink.inputs.base_directory = out_dir

    metco2_wf.connect([
        (inputnode, gen_stims, [('events', 'event_list')]),
        (gen_stims, deconvolve, ['stim_tuples', 'stim_times']),
        (inputnode, deconvolve, [('images', 'in_files'),
                                 (('events', len), 'num_stimts')]),
        (deconvolve, syn, [('cbucket', 'cbucket'),
                           ('x1D', 'matrix')]),
        (inputnode, datasink, [('subject_id', 'container')]),
        (syn, datasink, [('out_file', 'physio_corr')])
    ])

    return metco2_wf


def _gen_stim_list(event_list):
    """
    Given a list of event files, generate a list
    of tuples with the form (number, filename, HRF)
    for use in deconvolving the MRI timeseries.

    Inputs
    ------
    events: list
        A list of file names

    Outputs
    -------
    list
        a list of tuples of form (number, filename, HRF)
    """
    stim_tuples = []

    for i in range(len(event_list)):
        stim_tuples.append((i, event_list[i], 'SPMG1'))

    return stim_tuples