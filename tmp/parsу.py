import re

# Функция для извлечения числа из строки
def extract_number(line):
    match = re.search(r'NOTE: Time from the start to end of checking sstate availability == (\d+)', line)
    if match:
        return match.group(1)
    return None

# Открываем файл для записи результатов
with open('result.txt', 'w') as result_file:
    # Цикл по файлам с именами 2, 3, 4 и т.д.
    for file_number in range(2, 16):  # Вы можете изменить диапазон в зависимости от ваших нужд
        file_name = f"{file_number}"

        try:
            with open(file_name, 'r') as file:
                for line in file:
                    number = extract_number(line)
                    if number:
                        result_file.write(f"{file_name}_{number}\n")
                        break  # Прекращаем чтение файла после нахождения нужной строки
        except FileNotFoundError:
            result_file.write(f"{file_name}_{None}\n")
