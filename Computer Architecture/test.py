one = 1
debug

# instructions & iterations
instructions = ["LD.D F0,0(R1)",
	"ADD.D F4,F0,F2",
	"SD.D F4,0(R1)",
	"DADDIU R1,R1,#-8",
	"BNE R1,R2,L00P",
	]
iterations = 3

# maintain global variables
cycle_count = 1
program_counter = 0
target_registers = []  # Records the destination register of the variable to be written back, Free when the variable is written on CDB. Solve RAW, i.e. data waiting
instruction_status = []  # Records the status of instructions, when commit, update table pipeline
resource_utilization = []  # Records the utilization of function units by cycle
integer_unit_utilization = 0  # number of times int unit is used
fp_unit_utilization = 0
address_unit_utilization = 0
data_cache_utilization = 0
cdb0_utilization = 0
cdb1_utilization = 0

# Init instruction status
for i in range(iterations):
    for item in instructions:
        opcode, rest = item.split()
        destination_register, source_register1, source_register2 = 0, 0, 0  # Default value
        issue_cycles_left = 1  # Cycles left, indicate the current status
        execute_cycles_left = 1
        memory_access_cycles_left = 1
        write_cycles_left = 1

        if opcode == "ADD.D":
            destination_register, source_register1, source_register2 = rest.split(",")
            alu_type = "fp"
            execute_cycles_left = 3
            memory_access_cycles_left = 0
        elif opcode == "DADDIU":
            destination_register, source_register1, source_register2 = rest.split(",")
            alu_type = "int"
            memory_access_cycles_left = 0
        elif opcode == "LD.D":
            destination_register, address = rest.split(",")
            immediate_value, source_register1 = address.split("(")
            source_register1 = source_register1[:-1]
            alu_type = "addr"
        elif opcode == "SD.D":
            source_register2, address = rest.split(",")
            immediate_value, source_register1 = address.split("(")
            source_register1 = source_register1[:-1]
            alu_type = "addr"
            write_cycles_left = 0
        elif opcode == "BNE":
            source_register1, source_register2, _ = rest.split(",")
            alu_type = "int"
            memory_access_cycles_left = 0
            write_cycles_left = 0
        else:
            raise Exception("Invalid instruction![sim.py]")

        temp = {"iter": i + 1, "inst": item, "opcode": opcode, "rd": destination_register,
                "rs1": source_register1, "rs2": source_register2, "imm": immediate_value,
                "alu": alu_type, "issue": issue_cycles_left, "execute": execute_cycles_left,
                "mem_acc": memory_access_cycles_left, "write": write_cycles_left,
                "issue_cycle": "", "execute_cycle": "", "mem_acc_cycle": "", "write_cycle": "", "comment": ""}
        instruction_status.append(temp)

if one:
    for i in instruction_status:
        print(i)

# Update by cycle
max_length = iterations * len(instructions)
commit_count = 0

while commit_count < max_length:
    # Init the valid vector, when an instruction is executed in one stage, it becomes invalid, preventing multi-execution in one cycle
    valid_vector = [1, ] * max_length
    int_alu_available = 1
    fp_alu_available = 1
    addr_alu_available = 1
    cdb_valid_count = 2
    resource_units = {"int": "", "fp": "", "addr": "", "dcache": "", "CDB0": "", "CDB1": ""}

    # Issue
    if program_counter == max_length - 1:
        instruction_status[program_counter]["issue_cycle"] = cycle_count
        instruction_status[program_counter]["issue"] -= 1
        valid_vector[program_counter] = 0
        if instruction_status[program_counter]["rd"] != 0:
            temp = (program_counter, instruction_status[program_counter]["rd"])
            target_registers.append(temp)
        program_counter += 1
    elif program_counter < max_length - 1:
        alu1_type = instruction_status[program_counter]["alu"]
        alu2_type = instruction_status[program_counter + 1]["alu"]
        op1_code = instruction_status[program_counter]["opcode"]
        op2_code = instruction_status[program_counter + 1]["opcode"]

        if alu1_type == alu2_type or op1_code == "BNE" or op2_code == "BNE":  # Branch must operate separately, only issue one instruction
            # Update instruction_status
            instruction_status[program_counter]["issue_cycle"] = cycle_count
            instruction_status[program_counter]["issue"] -= 1
            valid_vector[program_counter] = 0
            if instruction_status[program_counter]["rd"] != 0:
                temp = (program_counter, instruction_status[program_counter]["rd"])
                target_registers.append(temp)
            program_counter += 1
        else:  # Issue two instructions
            # Update instruction_status
            instruction_status[program_counter]["issue_cycle"] = cycle_count
            instruction_status[program_counter + 1]["issue_cycle"] = cycle_count
            instruction_status[program_counter]["issue"] -= 1
            instruction_status[program_counter + 1]["issue"] -= 1
            valid_vector[program_counter] = 0
            valid_vector[program_counter + 1] = 0
            if instruction_status[program_counter]["rd"] != 0:
                temp = (program_counter, instruction_status[program_counter]["rd"])
                target_registers.append(temp)
            if instruction_status[program_counter + 1]["rd"] != 0:
                temp = (program_counter + 1, instruction_status[program_counter + 1]["rd"])
                target_registers.append(temp)
            program_counter += 2

    # Execute
    for idx in range(commit_count, program_counter):
        # Whether can update
        if instruction_status[idx]["issue"] == 0 and instruction_status[idx]["execute"] > 0 and valid_vector[idx] != 0:
            # Check RAW
            source_reg1 = instruction_status[idx]["rs1"]
            source_reg2 = instruction_status[idx]["rs2"]
            alu_type = instruction_status[idx]["alu"]
            raw_dependency = 0

            for item in target_registers:
                pc_executed, rd_executed = item

                if (source_reg1 == rd_executed or source_reg2 == rd_executed) and idx > pc_executed:
                    raw_dependency = 1
                    op_executed = instruction_status[pc_executed]["opcode"]
                    instruction_status[idx]["comment"] = "Wait for " + op_executed
                    break

            if not raw_dependency:
                if alu_type == "fp":
                    if fp_alu_available:
                        fp_alu_available -= 1
                        res = str(instruction_status[idx]["iter"]) + "/" + instruction_status[idx]["opcode"]
                        resource_units["fp"] = res
                        fp_unit_utilization += 1
                        if instruction_status[idx]["execute"] == 3:
                            instruction_status[idx]["execute_cycle"] = cycle_count
                    else:
                        instruction_status[idx]["comment"] = "Wait for FP ALU"
                elif alu_type == "int":
                    if int_alu_available:
                        int_alu_available -= 1
                        res = str(instruction_status[idx]["iter"]) + "/" + instruction_status[idx]["opcode"]
                        resource_units["int"] = res
                        integer_unit_utilization += 1
                        instruction_status[idx]["execute_cycle"] = cycle_count
                    else:
                        instruction_status[idx]["comment"] = "Wait for INT ALU"
                elif alu_type == "addr":
                    addr_alu_available -= 1
                    res = str(instruction_status[idx]["iter"]) + "/" + instruction_status[idx]["opcode"]
                    resource_units["addr"] = res
                    address_unit_utilization += 1
                    instruction_status[idx]["execute_cycle"] = cycle_count
                instruction_status[idx]["execute"] -= 1
                valid_vector[idx] = 0

    # Memory access
    for idx in range(commit_count, program_counter):
        # Whether can update
        if instruction_status[idx]["issue"] == 0 and instruction_status[idx]["execute"] == 0 \
                and instruction_status[idx]["mem_acc"] > 0 and valid_vector[idx] != 0:
            instruction_status[idx]["mem_acc"] -= 1
            res = str(instruction_status[idx]["iter"]) + "/" + instruction_status[idx]["opcode"]
            resource_units["dcache"] = res
            data_cache_utilization += 1
            instruction_status[idx]["mem_acc_cycle"] = cycle_count
            valid_vector[idx] = 0

    # Write CDB
    for idx in range(commit_count, program_counter):
        # Whether can update
        if instruction_status[idx]["issue"] == 0 and instruction_status[idx]["execute"] == 0 \
                and instruction_status[idx]["mem_acc"] == 0 and instruction_status[idx]["write"] > 0 \
                and valid_vector[idx] != 0:

            if cdb_valid_count == 2:
                cdb_valid_count -= 1
                res = str(instruction_status[idx]["iter"]) + "/" + instruction_status[idx]["opcode"]
                resource_units["CDB0"] = res
                cdb0_utilization += 1
                instruction_status[idx]["write"] -= 1
                instruction_status[idx]["write_cycle"] = cycle_count
                destination_reg = instruction_status[idx]["rd"]
                temp = (idx, destination_reg)
                if one: print(cycle_count, destination_reg)
                target_registers.remove(temp)
                valid_vector[idx] = 0
            elif cdb_valid_count == 1:
                cdb_valid_count -= 1
                res = str(instruction_status[idx]["iter"]) + "/" + instruction_status[idx]["opcode"]
                resource_units["CDB1"] = res
                cdb1_utilization += 1
                instruction_status[idx]["write"] -= 1
                instruction_status[idx]["write_cycle"] = cycle_count
                destination_reg = instruction_status[idx]["rd"]
                temp = (idx, destination_reg)
                if one: print(cycle_count, destination_reg)
                target_registers.remove(temp)
                valid_vector[idx] = 0
            else:
                instruction_status[idx]["comment"] = "Wait for CDBs"

    # Commit (all stages are 0)
    new_commit_count = commit_count
    for idx in range(commit_count, program_counter):  # Commit in order
        if instruction_status[idx]["issue"] == 0 and instruction_status[idx]["execute"] == 0 \
                and instruction_status[idx]["mem_acc"] == 0 and instruction_status[idx]["write"] == 0:
            new_commit_count += 1
        else:
            break
    commit_count = new_commit_count

    resource_utilization.append(resource_units)
    cycle_count += 1

    if one:
        print("*" * 20)
        print(cycle_count)
        print(valid_vector)
        print("target_registers", target_registers)
        print("commit_count=", commit_count, "program_counter=", program_counter)
        for i in instruction_status:
            print(i)

cycle_count -= 1

from prettytable import PrettyTable

def add_row_to_table(table, data, headers=None):
    if headers:
        table.field_names = headers
    table.add_row(data)

def print_table(table, title):
    print(title)
    print(table)

# Init tables and print results
pipeline_headers = ["Iter.#", "Instructions", "Issue", "Execution", "Mem. Access", "Write CDB", "Comment"]
resource_headers = ["Clock", "Int ALU", "FP ALU", "Addr. Adder", "Data Cache", "CDB0", "CDB1"]

pipeline_table = PrettyTable()
resource_table = PrettyTable()

for idx in range(max_length):
    add_row_to_table(pipeline_table, [instruction_status[idx]["iter"],
                                      instruction_status[idx]["inst"],
                                      instruction_status[idx]["issue_cycle"],
                                      instruction_status[idx]["execute_cycle"],
                                      instruction_status[idx]["mem_acc_cycle"],
                                      instruction_status[idx]["write_cycle"],
                                      instruction_status[idx]["comment"]], pipeline_headers)

for idx in range(cycle_count):
    add_row_to_table(resource_table, [idx + 1,
                                       resource_utilization[idx]["int"],
                                       resource_utilization[idx]["fp"],
                                       resource_utilization[idx]["addr"],
                                       resource_utilization[idx]["dcache"],
                                       resource_utilization[idx]["CDB0"],
                                       resource_utilization[idx]["CDB1"]], resource_headers)

total_row = ["Total", integer_unit_utilization, fp_unit_utilization, address_unit_utilization,
             data_cache_utilization, cdb0_utilization, cdb1_utilization]
utilization_row = ["Util%", integer_unit_utilization / cycle_count, fp_unit_utilization / cycle_count,
                   address_unit_utilization / cycle_count, data_cache_utilization / cycle_count,
                   cdb0_utilization / cycle_count, cdb1_utilization / cycle_count]

add_row_to_table(resource_table, total_row)
add_row_to_table(resource_table, utilization_row)

print_table(pipeline_table, "A Dual-issue Version of Tomasulo Pipeline")
print_table(resource_table, "Resource Usage Table")
print("ExecutionRate=", max_length / cycle_count)
