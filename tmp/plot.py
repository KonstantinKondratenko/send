import matplotlib.pyplot as plt

# Функция для чтения данных из файла
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

# Чтение данных из файла result.txt
file_name = 'result.txt'
numbers, values = read_data(file_name)

# Построение графика
plt.figure(figsize=(10, 6))
plt.plot(numbers, values, marker='o', linestyle='-', color='b')
plt.xlabel('Номер')
plt.ylabel('Число')
plt.title('Зависимость числа от номера')
plt.grid(True)
plt.show()
