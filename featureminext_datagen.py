import sys
import pandas as pd
from tqdm import tqdm
import json

def readinventory(filename):
    """Read phoneme inventory and store in a dictionary."""
    featdict = {}
    allsegments = set()

    lines = [line.strip() for line in open(f'feature_sets/{filename}.txt')]
    fields = lines[0].split()
    for f in fields:
        featdict[f] = {}
        featdict[f]['name'] = f # name of the feature
        featdict[f]['+'] = set() # phonemes with a + for that feature
        featdict[f]['-'] = set() # phonemes with a - for that feature
    for i in range(1, len(lines)):
        thisline = lines[i]
        if len(thisline) == 0:
            continue
        linefields = thisline.split()
        if len(linefields)!= len(fields) + 1 :
            print(f"Field length mismatch on line {i+1}")
            quit()
        phoneme = linefields[0]
        allsegments |= {phoneme}
        for j in range(1,len(linefields)):
            if linefields[j] == '+' or linefields[j] == '-':
                featdict[fields[j-1]][linefields[j]] |= {phoneme}

    return featdict, allsegments

def reccheck(fd, basefeats, basemodes, feats, modes, correct, baseindex):
    """
    Start with an empty set of features and keep adding features one by one with different starting phonemes, generating all possible unique feature combinations.
    Check if the generated feature combinations are natural classes for the given phoneme.
    """

    def store_feats(fd, feats, modes):
        """Store features for one solution in dictionary indexed by length."""
        global solutions
        length = len(feats)
        if length not in solutions:
            solutions[length] = []
        thissol = []
        for idx, feat in enumerate(feats):
            thissol.append(modes[idx] + fd[feat]['name'])
        solutions[length].append('[' + ','.join(thissol) + ']')
        if verbose:
            print('[' + ','.join(thissol) + ']')
            
    def check_feats(fd, feats, modes, correct):
        """Check if proposed feature combination is a valid solution."""
        newbase = allsegments
        for idx, feat in enumerate(feats):
            mode = modes[idx]
            newbase = newbase & fd[feat][mode]
        if newbase != correct:
            return False
        return True
        
    global maxlen
    if len(feats) > maxlen: # Bound the search (max: total amount of features)
        return
    if check_feats(fd, feats, modes, correct): # New solution
        store_feats(fd, feats, modes) # if proposed feature combination is a natural class, store solution
        if len(feats) < maxlen:
            maxlen = len(feats)
    numelem = len(basefeats)
    # This for loop iterates over all possible indeces and generates all possible feature combinations
    for i in range(baseindex, numelem):  # Add one feature
        if basefeats[i] not in feats:    # If we didn't add this already
            reccheck(fd, basefeats, basemodes, feats + [basefeats[i]], modes + [basemodes[i]], correct, i + 1)
    return

def greedy(fd, basefeats, basemodes, correct):
    """Implement greedy search based on C."""
    feats = []
    modes = []
    currentset = allsegments
    bestfeatures = []
    # Find most distinguishing feature
    while True:
        sols = []
        if verbose:
            print("===============================")
        for f,m in zip(basefeats, basemodes):
            extrasegs = (currentset & fd[f][m]) - correct
            length = len(extrasegs)
            if verbose:
                print("Len of " + fd[f]['name'] + " is " + str(length))
            sols.append((extrasegs, fd[f]['name'], length, m))
        bestsol = min(sols, key = lambda x: x[2])
        currentset = bestsol[0]
        bestfeatures.append(bestsol[3] + bestsol[1])

        if bestsol[2] == 0:
            break
    print("Greedy solution:", bestfeatures)

def get_general_info_natural_classes(natural_classes, keys):
    # if not os.path.exists(f'{language}_perphoneme_{inventoryfile}'):
    #     os.makedirs(f'{language}_perphoneme_{inventoryfile}')

    min_lengths = {} # store the length of the minimal description where each feature is included
    min_lengths_phonemes = {}
    avg_lengths = {key: [0,0] for key in keys} # store the average lengths of all descriptions per phoneme

    for phoneme in natural_classes:
        for sublist in natural_classes[phoneme]:
            sublist = sublist.strip("[]").split(',')
            # Iterate through each unique value
            for value in sublist:
                value = value.strip('+') # remove + symbols
                value = value.strip('-') # remove - symbols
                # Check if the value already exists in the dictionary
                if value in min_lengths:
                    # If the length of the current sublist is smaller than the stored length,
                    # update the stored length
                    min_lengths[value] = min(min_lengths[value], len(sublist))
                else:
                    # If the value doesn't exist in the dictionary, add it with the length
                    min_lengths[value] = len(sublist)

                if value in avg_lengths:
                    avg_lengths[value][0] += len(sublist)
                    avg_lengths[value][1] += 1
            
            if phoneme in min_lengths_phonemes:
                min_lengths_phonemes[phoneme] = min(min_lengths_phonemes[phoneme], len(sublist))
            else: 
                min_lengths_phonemes[phoneme] = len(sublist)
        
        # aux_plotting_function(min_lengths, f"Phoneme {phoneme}", 'Feature', 'Length minimal feature description', f'{language}_perphoneme_{inventoryfile}/{phoneme}.jpg', False)
                
    avg_lengths = {k: v[0] / v[1] if v[1] != 0 else 0 for k, v in avg_lengths.items()}

    min_descriptions = {} # store the minimal descriptions of each phoneme
    # get all minimal descriptions per phoneme
    for phoneme in natural_classes:
        if phoneme not in min_descriptions:
            min_descriptions[phoneme] = []

        for sublist in natural_classes[phoneme]:
            sublist = sublist.strip("[]").split(',')
            if min_lengths_phonemes[phoneme] == len(sublist):
                min_descriptions[phoneme].append(sublist)

    count_phoneme = {} # The number of times the feature is included in the minimal description of a phoneme
    count_lengths = {} # Count of minimal descriptions for various lengths
    # count features in minimal descriptions          
    for phoneme in min_descriptions:
        for sublist in min_descriptions[phoneme]:
            for value in sublist:
                value = value.strip('+') # remove + symbol
                value = value.strip('-') # remove - symbol
                if value in count_phoneme:
                    count_phoneme[value] += 1
                else:
                    count_phoneme[value] = 1
    
            if len(sublist) in count_lengths:
                count_lengths[len(sublist)] += 1
            else:
                count_lengths[len(sublist)] = 1
    
    return min_lengths, min_descriptions, count_phoneme, avg_lengths, count_lengths

def are_all_lists_empty(dictionary):
    return not any(dictionary.values())

def find_best_tree_recursive(partial_trees, idx, current_tree, minimal_descriptions, list_result):
    if any(current_tree.values()):
        list_result.append(current_tree.copy())
    
    for i in range(idx, len(partial_trees)):
        partial_tree = partial_trees[i]
        new_tree = {phoneme: list(set(partial_tree[phoneme]).union(current_tree[phoneme])) for phoneme in partial_tree}
        find_best_tree_recursive(partial_trees, i + 1, new_tree, minimal_descriptions, list_result)


def dicts_are_equal(dict1, dict2):
    return dict1.keys() == dict2.keys() and all(set(dict1[key]) == set(dict2[key]) for key in dict1)

def is_dict_in_list(dict_list, target_dict):
    return any(dicts_are_equal(d, target_dict) for d in dict_list)

def dict_to_tuple(d):
    return tuple((k, frozenset(v)) for k, v in sorted(d.items()))

def find_best_tree(minimal_descriptions_perphoneme, fd):
    """
    Find combinations of minimal feature descriptions that can form a tree together. That combination that has the most minimal descriptions 
    together will be the best tree. Those phonemes without any description yet can have any description that fits the tree (so no need to compute those)
    """

    print('\n-------------------------\n')

    # Get all partial trees
    partial_trees = []
    unique_trees = set()
    for phoneme, descriptions in minimal_descriptions_perphoneme.items():
        for description in descriptions:
            partial_tree = {key: [] for key in minimal_descriptions_perphoneme}
            features = [feature.strip().strip("+-") for feature in description.strip("[]").split(',')]

            for feature in features:
                for phoneme_plus in fd[feature]['+']:
                    if phoneme_plus in minimal_descriptions_perphoneme:
                        partial_tree[phoneme_plus].append(f'+{feature}')
                for phoneme_minus in fd[feature]['-']:
                    if phoneme_minus in minimal_descriptions_perphoneme:
                        partial_tree[phoneme_minus].append(f'-{feature}')

            # only store unique trees
            partial_tree_tuple = dict_to_tuple(partial_tree)

            if partial_tree_tuple not in unique_trees:
                unique_trees.add(partial_tree_tuple)
                partial_trees.append(partial_tree)

    list_result = []
    find_best_tree_recursive(partial_trees, 0, {key: [] for key in partial_trees[0]}, minimal_descriptions_perphoneme, list_result)

    best_trees = []
    best_count = 0
    stripped_descriptions_perphoneme = {phoneme: [set(item.strip("[]").split(',')) for item in descriptions]
            for phoneme, descriptions in minimal_descriptions_perphoneme.items()}
    for result in list_result:
        best = {}
        count = 0
        for phoneme in result:
            description = result[phoneme]
            if set(description) in stripped_descriptions_perphoneme[phoneme]:
                best[phoneme] = description
                count += 1
            else: best[phoneme] = []
        
        if count > best_count:
            best_count = count
            best_trees = [best]  # Reset the list with the new best tree
        elif count == best_count and not is_dict_in_list(best_trees, best):
            best_trees.append(best)  # Append to the list if it has the same best count and is not a duplicate

    return best_trees

##############################################################################

if len(sys.argv) < 1:
    print("Usage: " + sys.argv[0] + " [-v] inventoryfile")
    quit()


verbose = False
i = 1
if sys.argv[1] == '-v':
    verbose = True
    i += 1

inventoryfile = sys.argv[1]
fd, allsegments = readinventory(inventoryfile)
df = pd.read_csv('pb_languages_formatted.csv')
all_languages = {}
for index, row in tqdm(df.iterrows()):
    language = row['language'].replace("/", " or ")
    family = row['family']
    inventory = row['core inventory']
    inventory = inventory.strip("[]").split(',')
    inventory = [feature.strip().replace("'", "") for feature in inventory]
    inventory = [feature for feature in inventory if feature != '']
    allsegments = set(inventory)

    minimal_natural_classes = []
    minimal_natural_classes_perphoneme = {}
    natural_classes = []
    natural_classes_perphoneme = {}
    for testset in tqdm(allsegments):
        features = [f for f in fd]
        base = allsegments
        feats, modes = [], [] # list with featres, list with signs for each feature
        testset = {testset}
        # print("\nCalculating C for phoneme set " + str(testset))

        # Iterate over all features to find:
            # base: list of phonemes that are described by the same features as the given test phoneme
            # feats: list of features that describe the given phoneme
            # modes: list with the respective signs of the features describing the given phoneme
        for feat in features:
            if testset <= fd[feat]['+']: # test whether testset is a subset of fd[feat]['+']
                # fd[feat]['+']: set of phonemes that have the feature feat with sign + 
                base = base & fd[feat]['+'] # returns intersection between the two sets (those elements that are in both sets)
                # print("+" + fd[feat]['name'], end=' ')
                feats.append(feat)
                modes.append('+')
            elif testset <= fd[feat]['-']:
                # fd[feat]['-']: set of phonemes that have the feature feat with sign - 
                base = base & fd[feat]['-']
                # print("-" + fd[feat]['name'], end=' ')
                feats.append(feat)
                modes.append('-')
        # print()

        solutions = {}
        # with open(f'natural_classes_{inventoryfile}_{language}.txt', 'a') as file:
        #     file.write(f"\nPhoneme: {base}")
        if base == testset: # check if the procedure above has resulted in the phoneme being tested (i.e. we have the correct general feature description and it is a natural class)
            # file.write(f"\nPhoneme: {base}")
            # print("Set is a natural class")
            maxlen = len(feats)
            reccheck(fd, feats, modes, [], [], base, 0)
            for s in solutions.values():
                for a in s:
                    # Writing text
                    # file.write(f"\n{a}")
                    natural_classes.append(a) 
                    if list(testset)[0] in natural_classes_perphoneme:
                        natural_classes_perphoneme[list(testset)[0]].append(a)
                    else: 
                        natural_classes_perphoneme[list(testset)[0]] = []
            minsol = min(solutions.keys())
            for s in solutions[minsol]:
                minimal_natural_classes.append(s)
                if list(testset)[0] in minimal_natural_classes_perphoneme:
                    minimal_natural_classes_perphoneme[list(testset)[0]].append(s)
                else: 
                    minimal_natural_classes_perphoneme[list(testset)[0]] = []
            # else:
                # the given phoneme does not have a feature description that distinguishes it from all the other phonemes (i.e. does not form a natural class)
                # print("Set is not a natural class")

    min_lengths, min_descriptions, count_phoneme, avg_lengths, count_lengths = get_general_info_natural_classes(natural_classes_perphoneme, list(fd.keys()))
    all_languages[language] = {'min_lengths': min_lengths, 'min_descriptions': min_descriptions, 
                                'count_phoneme': count_phoneme, 'avg_lengths': avg_lengths, 'count_lengths': count_lengths}

with open(f'data_all_languages_{inventoryfile}.json', 'w') as file:
    json.dump(all_languages, file)