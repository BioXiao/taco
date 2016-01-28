'''
TACO: Transcriptome meta-assembly from RNA-Seq
'''
import logging
import collections
import networkx as nx

from path_graph import NODE_EXPR

__author__ = "Matthew Iyer and Yashar Niknafs"
__copyright__ = "Copyright 2016"
__credits__ = ["Matthew Iyer", "Yashar Niknafs"]
__license__ = "GPL"
__version__ = "0.4.0"
__maintainer__ = "Yashar Niknafs"
__email__ = "yniknafs@umich.edu"
__status__ = "Development"


# constant minimum path score
MIN_SCORE = 1.0e-10

# for dynamic programming algorithm
TMP_NODE_EXPR = 'tmpns'
PATH_MIN_SCORE = 'pmin'
PATH_PREV = 'pprev'

imax2 = lambda x, y: x if x >= y else y
imin2 = lambda x, y: x if x <= y else y


def init_tmp_attributes(G):
    '''
    set node attributes that are added to the graph temporarily
    '''
    # copy the node weights to a temporary variable so that we can
    # manipulation them in the algorithm and create path attributes
    # for dynamic programming
    for n, d in G.nodes_iter(data=True):
        d[TMP_NODE_EXPR] = d[NODE_EXPR]
        d[PATH_MIN_SCORE] = MIN_SCORE
        d[PATH_PREV] = None


def clear_tmp_attributes(G):
    '''
    remove node attributes that are added to the graph temporarily
    '''
    for n, d in G.nodes_iter(data=True):
        del d[TMP_NODE_EXPR]
        del d[PATH_MIN_SCORE]
        del d[PATH_PREV]


def reset_path_attributes(G):
    """
    must call this before calling the dynamic programming algorithm
    """
    # reset path attributes
    for n, d in G.nodes_iter(data=True):
        d[PATH_MIN_SCORE] = MIN_SCORE
        d[PATH_PREV] = None


def dynprog_search(G, source):
    """
    Find the highest scoring path by dynamic programming
    # Adapted from NetworkX source code http://networkx.lanl.gov
    """
    # setup initial path attributes
    reset_path_attributes(G)
    G.node[source][PATH_MIN_SCORE] = G.node[source][TMP_NODE_EXPR]
    # topological sort allows each node to be visited exactly once
    queue = collections.deque(nx.topological_sort(G))
    while queue:
        u = queue.popleft()
        path_min_score = G.node[u][PATH_MIN_SCORE]
        for v in G.successors_iter(u):
            v_attrs = G.node[v]
            v_score = v_attrs[TMP_NODE_EXPR]
            # compute minimum score that would occur if path
            # traversed through node 'v'
            new_min_score = imin2(path_min_score, v_score)
            # update if score is larger
            if ((v_attrs[PATH_PREV] is None) or
                (new_min_score > v_attrs[PATH_MIN_SCORE])):
                v_attrs[PATH_MIN_SCORE] = new_min_score
                v_attrs[PATH_PREV] = u


def traceback(G, sink):
    """
    compute path and its score
    """
    path = [sink]
    score = G.node[sink][PATH_MIN_SCORE]
    prev = G.node[sink][PATH_PREV]
    while prev is not None:
        path.append(prev)
        prev = G.node[prev][PATH_PREV]
    path.reverse()
    return tuple(path), score


def find_path(G, source, sink):
    """
    G - graph
    source, sink - start/end nodes
    """
    # dynamic programming search for best path
    dynprog_search(G, source)
    # traceback to get path
    path, score = traceback(G, sink)
    return path, score


def subtract_path(G, path, score):
    """
    subtract score from nodes along path
    """
    for i in xrange(len(path)):
        u = path[i]
        d = G.node[u]
        d[TMP_NODE_EXPR] = imax2(MIN_SCORE,
                                 d[TMP_NODE_EXPR] - score)


def find_suboptimal_paths(G, source, sink, fraction_major_path=1e-3,
                          max_paths=1000):
    """
    finds suboptimal paths through graph G using a greedy algorithm that
    finds the highest score path using dynamic programming, subtracts
    the path score from the graph, and repeats

    paths with score lower than 'fraction_major_path' are not
    returned.  algorithm may stop prematurely if 'max_paths' iterations
    have completed.
    """
    # setup temporary graph attributes
    init_tmp_attributes(G)
    # store paths in a dictionary in order to avoid redundant paths
    # that arise when the heuristic assumptions of the algorithm fail
    path_results = collections.OrderedDict()
    # find highest score path
    path, score = find_path(G, source, sink)
    path_results[path] = score
    subtract_path(G, path, score)
    # iterate to find suboptimal paths
    iterations = 1
    highest_score = score
    lowest_score = max(MIN_SCORE, highest_score * fraction_major_path)
    while iterations < max_paths:
        # find path
        path, score = find_path(G, source, sink)
        if score <= lowest_score:
            break
        # store path
        if path not in path_results:
            path_results[path] = score
        # TODO: remove assert
        assert highest_score >= score
        # subtract path score from graph and resort seed nodes
        subtract_path(G, path, score)
        iterations += 1
    logging.debug("\tpath finding iterations=%d" % iterations)
    # cleanup graph attributes
    clear_tmp_attributes(G)
    # return (path,score) tuples sorted from high -> low score
    return path_results.items()
