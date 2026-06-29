import ast


KB = { #a dictonery to store the KB values
    "executions":0,
    "numAppearences":{},
    "faults":{},
    "actions":{},
    "tests":{},
    "symptoms":{},
    "nonapplicable": set()
}

def load_KB(filepath): #a function that will load the KB in the coad and store it in the dictonery
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.endswith('.'):
                line = line[:-1]
            if not line:
                continue 
            if line.startswith("executions("):
                KB["executions"] = int(line.split('(')[1].split(')')[0])
            elif line.startswith("numAppearences("):
                string = line.split('(')[1].split(')')[0].split(',')
                fault_id = int(string[0].strip())
                count = int(string[1].strip())
                KB["numAppearences"][fault_id]=count
            elif line.startswith("fault("):
                string = line.split('(')[1].split(')')[0].split(",", 2)
                fault_id = int(string[0].strip())
                description = string[1].strip().strip('"')
                rest = string[2].strip()

                list_start = rest.find('[')
                list_end = rest.find(']') + 1
                symptoms_list_str = rest[list_start:list_end]
                symptoms_id = ast.literal_eval(symptoms_list_str)

                rest_after_list = rest[list_end:].strip().lstrip(',').split(',')
                test_id = int(rest_after_list[0].strip())
                action_id = int(rest_after_list[1].strip())

                KB["faults"][fault_id] = {
                    "description": description,
                    "symptoms": symptoms_id,
                    "test_id": test_id,
                    "action_id": action_id
                }

            elif line.startswith("action("):
                string =  line.split('(')[1].split(')')[0].split(',')
                actions_id = int(string[0].strip())
                description = string[1].strip().strip('"')
                KB['actions'][actions_id] = description
            elif line.startswith("test("):
                string = line.split('(')[1].split(')')[0].split(',')
                test_id = int(string[0].strip())
                description = string[1].strip().strip('"')
                KB['tests'][test_id] = description
            elif line.startswith("symptom("):
                string = line.split('(')[1].split(')')[0].split(',')
                symptom_id = int(string[0].strip())
                description = string[1].strip().strip('"')
                KB['symptoms'][symptom_id] = description
            elif line.startswith("nonapplicable("):
                fault_id = int(line.split('(')[1].split(')')[0])
                KB["nonapplicable"].add(fault_id)

def update_executions(): #this function will update the number of executions that the KB has 
    KB["executions"]+=1


def find_minimal_candidates(observed_symptoms): #this function finda the minimal candidates 

    symptom_fault_sets = []
    for sym in observed_symptoms:
        fault_per_symptom = set()
        for fault_id in KB["faults"]:
            current_fault = KB["faults"][fault_id]
            if fault_id not in KB["nonapplicable"] and sym in current_fault["symptoms"]:
                fault_per_symptom.add(fault_id)

        symptom_fault_sets.append(fault_per_symptom) #this list gives evry fault that might cause a symptom (for example for symptoms (1,2) it might give something like this {[1,2,3],[2,3]})
    
    
    relevant_faults_set = set()
    for fault_set in symptom_fault_sets:
        relevant_faults_set.update(fault_set) #this prosses get all the unige fauts that apper in the symptom_fault_sets list

    relevant_faults = sorted(relevant_faults_set) 


    hitting_sets = []

    def backtracking(partial_candidate, index_start, symptoms_explaind): #this funcytin generates the candidates recursivly one by one 
        if len(symptoms_explaind) == len(symptom_fault_sets):
            hitting_sets.append(frozenset(partial_candidate))
            return
        
        if index_start >= len(relevant_faults):
            return

        for i in range(index_start, len(relevant_faults)):
            fault_tested = relevant_faults[i]

            new_sym_ex = symptoms_explaind.copy()
            for idx, fault_set in enumerate(symptom_fault_sets):
                if idx not in new_sym_ex and fault_tested in fault_set:
                    new_sym_ex.add(idx)

            backtracking(partial_candidate+[fault_tested], i+1, new_sym_ex) #this is how the backtraking function is called for the next loop

    backtracking([],0,set()) #this is the original call of the backtraking function

    sorted_hitting_sets = sorted(list(hitting_sets), key=len) #this sorts the candidates from smallest to largest

    minimun_candidates = []
    for Current_hitting_set in sorted_hitting_sets:
        is_minimal = True
        for existing_minimal_hs in minimun_candidates:
            if existing_minimal_hs.issubset(minimun_candidates):
                is_minimal=False
                break 
            
        if is_minimal:
            minimun_candidates.append(Current_hitting_set) #this stors only the minimla candidates

    return[set(mc) for mc in minimun_candidates] #this turns the frozenset back to a normal set

def get_symptoms(fault_set): #this function gets all the symotoms that may be casued by the faults in the curent fault set
    all_symptoms = set()
    for fault_id in fault_set:
        if fault_id in KB["faults"]:
            all_symptoms.update(KB["faults"][fault_id]["symptoms"])
    return all_symptoms

def calculate_likelihood(candidate_set, observed_symptoms): #this function is used to calculate the likehood of each candidate in roder to sort them later
    if KB["executions"] == 0:
        return 0.0, len(candidate_set), len(get_symptoms(candidate_set) - observed_symptoms)
    
    likelihood = 1.0
    for fault in candidate_set:
        likelihood *= KB["numAppearences"].get(fault,0)/KB["executions"]
    
    num_faults = len(candidate_set)

    all_symptoms = get_symptoms(candidate_set)
    unobserved_symptoms = len(all_symptoms - observed_symptoms)

    return likelihood, num_faults, unobserved_symptoms

def sort_candidates(candidates, observed_symptoms): #htis sorts the candidate
    return sorted(candidates, key=lambda c: (-calculate_likelihood(c, observed_symptoms)[0], calculate_likelihood(c, observed_symptoms)[1], 
    calculate_likelihood(c, observed_symptoms)[2]))

def choose_fault(candidate_set, observed_symptoms): #this chooses the best fault in the first candidate 
    best_fault = None
    most_symptoms_explaned = -1

    for fault in candidate_set:
        fault_symptoms = set(KB["faults"][fault]["symptoms"])
        symptoms_explaind = len(fault_symptoms.intersection(observed_symptoms))

        if symptoms_explaind > most_symptoms_explaned:
            most_symptoms_explaned = symptoms_explaind
            best_fault = fault
    return best_fault

def logic_loop(): #this is the main loop for the code 
    update_executions()

    print('number of executions: ', KB["executions"])
    print('select on of the following symptoms: ')
    for sym_id, description in KB["symptoms"].items():
        print("Symptom: ", sym_id ,":", description)
    symptom_input = input("Enter the symptom id's you see (seperated with commas eg. 1,2): ")
    observed_symptoms = set()
    if symptom_input.strip():
        try:
            for s_id in symptom_input.strip().split(','):
                symptom = int(s_id)
                if symptom in KB["symptoms"]:
                    observed_symptoms.add(symptom)
                else:
                    print("Warning ", symptom," not valid since it was not found in the knowledge base, ignoring \n")
        except ValueError:
            print("Invalid input, try again")

    while True:
        if not observed_symptoms:
            print("no Symptoms detected ending diagnostic system \n")
            break
        
        print("computing the minimal candidates \n")
        minimal_candidates = find_minimal_candidates(observed_symptoms)

        if not minimal_candidates:
            print("couldn't find any minimal candidates, exiting \n")
            break

        print("sorting the candidates\n")
        sorted_candidates = sort_candidates(minimal_candidates, observed_symptoms)

        print("picking the best fault\n")
        first_candidate = sorted_candidates[0]
        fault_to_test = choose_fault(first_candidate, observed_symptoms)

        if not fault_to_test:
            print("couldn't choose fault, exiting \n")
            break

        fault_description = KB["faults"][fault_to_test]["description"]
        test_id = KB["faults"][fault_to_test]["test_id"]
        test_description = KB["tests"][test_id]

        print(f"most likly fault is: {fault_description}\n")

        print(f"test for '{fault_description}', test: '{test_description}'\n")

        test_input = input("was the fault present after the test? (yes/no)").lower().strip()

        if test_input == 'yes':
            KB["numAppearences"][fault_to_test] = KB["numAppearences"].get(fault_to_test, 0) + 1
            print(f"Updated appearance count for fault '{fault_description}'. New count: {KB['numAppearences'][fault_to_test]}")
            action_id = KB["faults"][fault_to_test]["action_id"]
            action_description = KB["actions"][action_id]

            print(f"the action for '{fault_description}' action: {action_description}\n")
            
            action_input = input("press enter when the action is applied")

            KB["nonapplicable"].add(fault_to_test)
            print(f"Fault '{fault_description}' set to 'non-applicable' state.")
        elif test_input == 'no':
            print(fault_description ," was not present, fault is non aplicable")
            KB["nonapplicable"].add(fault_to_test)
        else:
            print("Invalid input. Please answer 'yes' or 'no'. Diagnosis will continue with current state.")
            continue 
        
        print('select on of the following symptoms: ')
        for sym_id, description in KB["symptoms"].items():
            print("Symptom: ", sym_id ,":", description)
        new_symptom_input = input("Enter the symptom id's you see (seperated with commas eg. 1,2) or press enter if no new symptoms appear: ")
        new_observed_symptoms = set()
        if new_symptom_input.strip():
            try:
                for s_id in new_symptom_input.strip().split(','):
                    symptom = int(s_id)
                    if symptom in KB["symptoms"]:
                        new_observed_symptoms.add(symptom)
                    else:
                        print("Warning ", symptom ,"not valid since it was not found in the knowledge base, ignoring")
            except ValueError:
                print("Invalid input, try again")
                continue

        if not new_observed_symptoms:
            print('\nno new symptoms are found exiting system')
            break
        else:
            print("\nNew symptoms observed. Restarting diagnostic process...\n")
            update_executions()
            observed_symptoms = new_observed_symptoms
            print('number of executions: ', KB["executions"],'\n')
def main(): #this is the main function that loads the KB and then calles the logic loop function
    kb = "knowledge_base.txt"
    try:
        load_KB(kb)
        print("Knowledge Base loaded successfully.")
        logic_loop()
    except FileNotFoundError:
        print(f"Error: Knowledge base file '{kb}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


