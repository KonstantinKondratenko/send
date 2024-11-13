import matplotlib.pyplot as plt

def read_data(file_name):
    numbers = []
    values = []
    with open(file_name, 'r') as file:
        for line in file:
            parts = line.strip().split('_')
            if len(parts) == 2:
                number = int(parts[0])
                value = int(parts[1])
                numbers.append(number)
                values.append(value)
    return numbers, values

file_name1 = 'result_before.txt'
file_name2 = 'result_after.txt'

numbers1, values1 = read_data(file_name1)
numbers2, values2 = read_data(file_name2)

plt.figure(figsize=(10, 6))
plt.plot(numbers1, values1, marker='o', linestyle='-', color='b', label='result before')
plt.plot(numbers2, values2, marker='o', linestyle='-', color='r', label='result after')
plt.xlabel('Number of servers')
plt.ylabel('Time from the start of the build to the end of signature verification (sec)')
plt.title('Dependency of time on the number of servers [log scale]')
# plt.xscale('log')
plt.yscale('log')
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.legend()

plt.savefig('log_plot.png')
plt.close()
