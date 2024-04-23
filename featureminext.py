import sys
import matplotlib.pyplot as plt
from ordered_set import OrderedSet
import os

def readinventory(filename):
    """Read phoneme inventory and store in a dictionary."""
    featdict = {}
    allsegments = set()

    lines = [line.strip() for line in open(filename)]
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
        if len(linefields) != len(fields) + 1:
            print("Field length mismatch on line " + i+1)
            quit()
        phoneme = linefields[0]
        allsegments |= {phoneme}
        for j in range(1,len(linefields)):
            if linefields[j] == '+' or linefields[j] == '-':
                featdict[fields[j-1]][linefields[j]] |= {phoneme}

    return featdict, allsegments

# First call: reccheck(fd, feats, modes, [], [], base, 0) 
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

def find_smallest_sublist_length(lst):
    min_lengths = {}

    for sublist in lst:
        sublist = sublist.strip("[]").split(',')
        # Iterate through each unique value
        for value in sublist:
            value = value.strip('+')
            value = value.strip('-')
            # Check if the value already exists in the dictionary
            if value in min_lengths:
                # If the length of the current sublist is smaller than the stored length,
                # update the stored length
                min_lengths[value] = min(min_lengths[value], len(sublist))
            else:
                # If the value doesn't exist in the dictionary, add it with the length
                min_lengths[value] = len(sublist)

    return min_lengths

def find_avg_sublist_length(lst, keys):
    avg_lengths = {key: [0,0] for key in keys}
    for sublist in lst:
        sublist = sublist.strip("[]").split(',')
        for value in sublist:
            value = value.strip('+')
            value = value.strip('-')
            if value in avg_lengths:
                avg_lengths[value][0] += len(sublist)
                avg_lengths[value][1] += 1

    return {k: v[0] / v[1] for k, v in avg_lengths.items()}

def find_best_tree(features, segments, order, fd, idx, trees):
    def get_feat_description(ordered_feat, feat_dict, seg):
        feat_description = []
        mode_description = []
        for feat in ordered_feat:
            if seg <= feat_dict[feat]['+']:
                feat_description.append(feat)
                mode_description.append('+')
            elif seg <= feat_dict[feat]['-']:
                feat_description.append(feat)
                mode_description.append('-')
        return feat_description, mode_description
    
    def check_feats(fd, feats, modes, correct):
        """Check if proposed feature combination is a valid solution."""
        newbase = allsegments
        for idx, feat in enumerate(feats):
            mode = modes[idx]
            newbase = newbase & fd[feat][mode]
        if newbase != correct:
            return False
        return True
    
    """
    - Iterate over features:
        - find segments that are described by that feature (either with + or - signs)
        - check if the added feature generates a natural class for each segment
        - add the feature to the descriptions of those phoneme that have that feature
    - store the resulting feature descriptions generated with that tree
    Return: a dictionary where keys represent the order in which the features were applied and the values are dictionaries with the natural 
    class generated for each phoneme
    """
    # iterate over features
    nat_classes = {}
    for i in range(idx, len(features)):
        order.append(features[i]) # keep track of the order of the features
        segments = segments & (fd[features[i]]['+'] + fd[features[i]]['-']) # find segments being described by given feature
        for seg in segments:
            if seg not in nat_classes[seg]: # only continue if no natural class has been found for that segment yet
                feats, modes = get_feat_description(order, fd, seg) # get feature description of the segment for the given feature order so far
                if check_feats(fd, feats, modes, seg): # check if the description is a natural class for the given segment
                    nat_classes[seg] = [feats, modes]
        find_best_tree(features[i], segments, order, fd, idx + 1, trees)
    trees[order] =  nat_classes
    return order
# find_best_tree(features, allsegments, OrderedSet([]), fd, 0, {})

##############################################################################

if len(sys.argv) < 2:
    print("Usage: " + sys.argv[0] + " [-v] inventoryfile phonemeset")
    quit()

verbose = False
i = 1
if sys.argv[1] == '-v':
    verbose = True
    i += 1

inventoryfile = sys.argv[i]
fd, allsegments = readinventory(inventoryfile)

if len(sys.argv) == 3:
    language = sys.argv[2]
    with open(f"{language}.txt", "r") as file:
        lines = file.readlines()
    selected_segments = [line.strip() for line in lines]
    allsegments = set(selected_segments)

print(allsegments)
minimal_natural_classes = []
natural_classes = []
for testset in allsegments:
    features = [f for f in fd]
    base = allsegments
    feats, modes = [], [] # list with featres, list with signs for each feature
    testset = set(testset)
    print("Calculating C for phoneme set " + "{" + ','.join(testset) + "}")

    # Iterate over all features to find:
        # base: list of phonemes that are described by the same features as the given test phoneme
        # feats: list of features that describe the given phoneme
        # modes: list with the respective signs of the features describing the given phoneme
    for feat in features:
        if testset <= fd[feat]['+']: # test whether testset is a subset of fd[feat]['+']
            # fd[feat]['+']: set of phonemes that have the feature feat with sign + 
            base = base & fd[feat]['+'] # returns intersection between the two sets (those elements that are in both sets)
            print("+" + fd[feat]['name'], end=' ')
            feats.append(feat)
            modes.append('+')
        elif testset <= fd[feat]['-']:
            # fd[feat]['-']: set of phonemes that have the feature feat with sign - 
            base = base & fd[feat]['-']
            print("-" + fd[feat]['name'], end=' ')
            feats.append(feat)
            modes.append('-')
    print()

    solutions = {}
    with open(f'natural_classes_{inventoryfile}_{language}.txt', 'a') as file:
        if base == testset: # check if the procedure above has resulted in the phoneme being tested (i.e. we have the correct general feature description and it is a natural class)
            file.write(f"\nPhoneme: {base}")
            print("Set is a natural class")
            print("Trying branch-and-bound")
            maxlen = len(feats)
            reccheck(fd, feats, modes, [], [], base, 0)
            for s in solutions.values():
                for a in s:
                    # Writing text
                    file.write(f"\n{a}")
                    natural_classes.append(a)  
            minsol = min(solutions.keys())
            print("Minimal solution(s):")
            for s in solutions[minsol]:
                print(s)
                minimal_natural_classes.append(s)
            print("Trying greedy search")
            greedy(fd, feats, modes, base)
        else:
            # the given phoneme does not have a feature description that distinguishes it from all the other phonemes (i.e. does not have a natural class)
            print("Set is not a natural class")

min_order = find_smallest_sublist_length(minimal_natural_classes)
min_order = dict(sorted(min_order.items(), key=lambda item: item[1]))
classes = list(min_order.keys())
counts = list(min_order.values())

# Plot the histogram
plt.bar(classes, counts, width=0.8)
plt.xlabel('Feature')
plt.ylabel('Length minimal natural class')
plt.xticks(rotation=90)
plt.locator_params(axis="y", integer=True)
plt.savefig('minfeatureimportance.jpg', bbox_inches='tight')
plt.close()

avg_order = find_avg_sublist_length(natural_classes, list(fd.keys()))
avg_order = dict(sorted(avg_order.items(), key=lambda item: item[1]))
classes = list(avg_order.keys())
counts = list(avg_order.values())

# Plot the histogram
plt.bar(classes, counts, width=0.8)
plt.xlabel('Feature')
plt.ylabel('Average length natural classes')
plt.xticks(rotation=90)
plt.locator_params(axis="y", integer=True)
plt.savefig('avgfeatureimportance.jpg', bbox_inches='tight')
plt.close()