from typing import Tuple, List, Dict, Generator, Callable, Union, Any

from wibl.core import Lineage
from wibl.core.logger_file import DataPacket
from wibl.core.algorithm import WiblAlgorithm, AlgorithmPhase, AlgorithmDescriptor, UnknownAlgorithm
from wibl.core.algorithm.deduplicate import Deduplicate
from wibl.core.algorithm.nodatareject import NoDataReject


ALGORITHMS = {
    'deduplicate': Deduplicate,
    'nodatareject': NoDataReject
}


def _get_run_func_for_phase(algorithm: WiblAlgorithm, phase: AlgorithmPhase) -> \
        Callable[
            [Union[List[DataPacket], Dict[str, Any]], str, Lineage, bool],
            Union[List[DataPacket], Dict[str, Any]]
        ]:
    if phase is AlgorithmPhase.ON_LOAD:
        return algorithm.run_on_load
    elif phase is AlgorithmPhase.AFTER_TIME_INTERP:
        return algorithm.run_after_time_interp
    elif phase is AlgorithmPhase.AFTER_GEOJSON_CONVERSION:
        return algorithm.run_after_geojson_conversion


def iterate(algorithm_descriptors: List[AlgorithmDescriptor],
            phase: AlgorithmPhase,
            wibl_file_name: str) -> \
        Generator[
            Tuple[
                Callable[
                    [Union[List[DataPacket], Dict[str, Any]], str, Lineage, bool],
                    Union[List[DataPacket], Dict[str, Any]]
                ],
                str,
                str
            ], None, None]:
    """
    Iterate over all ``algorithm_descriptors`` (which will usually be read from WIBL files) yielding the
        phase-appropriate run function for each algorithm that can be applied to ``phase``.

    :param algorithm_descriptors: List of dicts containing the following keys: name, params
    :param phase: ``AlgorithmPhase`` with only a single value set.
    :param manager: ``ManagerInterface`` used to send log messages
    :param wibl_file_name: The name of the original WIBL file to which algorithms are to be applied, used for logging
        purposes.
    :return: For each algorithm defined in ``algorithm_descriptors``, this function yields a tuple whose first value is:
        ``run_on_load`` class method if ``phase`` is ``AlgorithmPhase.ON_LOAD``
        ``run_after_time_interp`` class method if ``phase`` is ``AlgorithmPhase.AFTER_TIME_INTERP``
        ``run_after_geojson_conversion`` class method if ``phase`` is ``AlgorithmPhase.AFTER_GEOJSON_CONVERSION``
        The second and third values of the yielded tuple will always be: algorithm name, algorithm parameters.
    :raises:
        UnknownAlgorithm: If an unknown algorithm is encountered.
    """
    for alg_desc in algorithm_descriptors:
        alg_name = alg_desc.name
        if alg_name in ALGORITHMS:
            alg: WiblAlgorithm = ALGORITHMS[alg_name]
            if phase in alg.phases:
                yield _get_run_func_for_phase(alg, phase), alg.name, alg_desc.params
        else:
            raise UnknownAlgorithm(f"Unknown algorithm '{alg_name}' for {wibl_file_name}.")


def run_algorithms(data: Union[List[DataPacket], Dict[str, Any]],
                   algorithms: List[AlgorithmDescriptor],
                   phase: AlgorithmPhase,
                   filename: str,
                   lineage: Lineage,
                   verbose: bool) -> Union[List[DataPacket], Dict[str, Any]]:
    """
    Run all algorithms defined in ``algorithms`` applicable to ``phase`` passing ``data``
    to each algorithm sequentially. ``data`` will be modified in place.
    :param data: Data to be processed.
    :param algorithms: Algorithms with which to process data.
    :param phase: WIBL processing phase to run algorithms for.
    :param filename: WIBL filename.
    :param lineage: Lineage object to record processing details.
    :param verbose: Verbose flag.
    :return:
    """
    if verbose:
        print(f"Applying requested algorithms for phase {phase} (if any) ...")
    for algorithm, alg_name, params in iterate(algorithms, phase, filename):
        if verbose:
            print(f'Applying algorithm {alg_name}')
        data = algorithm(data, params, lineage, verbose)
    return data
