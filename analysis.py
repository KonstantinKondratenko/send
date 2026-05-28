import os
import re
import numpy as np
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class TestCaseCollector:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.test_cases = []
        
    def collect(self):
        for entry in os.listdir(self.root_dir):
            lab_path = os.path.join(self.root_dir, entry)
            if self._is_valid_lab_dir(lab_path, entry):
                self._process_lab_dir(lab_path, entry)
        return self.test_cases
    
    def _is_valid_lab_dir(self, path, entry):
        return os.path.isdir(path) and ":" in entry and re.match(r'lab\d+', entry)
    
    def _process_lab_dir(self, lab_path, entry):
        match = re.match(r'lab(\d+)', entry)
        if match:
            lab_number = int(match.group(1))
            self.test_cases.extend(self._get_test_cases(lab_path, entry, lab_number))
    
    def _get_test_cases(self, lab_path, entry, lab_number):
        cases = []
        cpu_log = os.path.join(lab_path, 'cpu.log')
        ram_log = os.path.join(lab_path, 'ram.log')
        time_log = os.path.join(lab_path, f"{entry}:time.log")
        
        if all(os.path.isfile(f) for f in [cpu_log, ram_log, time_log]):
            cases.append({
                'lab_number': lab_number,
                'lab_name': entry,
                'cpu_log': cpu_log,
                'ram_log': ram_log,
                'time_log': time_log,
                'is_correct': 'correct' in entry.lower()
            })
        return cases

class LogParser:
    @staticmethod
    def parse_time_log(time_log_path):
        with open(time_log_path, 'r') as f:
            times = [float(line.strip()) for line in f if line.strip()]
        return sum(times) / len(times)
    
    @staticmethod
    def parse_cpu_log(cpu_log_path):
        cpu_data = []
        start_time = None
        skip_next_line = False
        with open(cpu_log_path, 'r') as f:
            for line in f:
                if skip_next_line:
                    skip_next_line = False
                    continue
                parts = line.strip().split()
                if not parts:
                    continue
                if 'RESET' in parts:
                    skip_next_line = True
                    continue
                if parts[0] == 'CPU' and len(parts) > 3:
                    timestamp = datetime.strptime(parts[3] + ' ' + parts[4], '%Y/%m/%d %H:%M:%S')
                    if start_time is None:
                        start_time = timestamp
                    numcpu = int(parts[7])
                    idle = float(parts[11])
                    cpu_usage = (100 * numcpu - idle) / numcpu
                    elapsed = (timestamp - start_time).total_seconds()
                    cpu_data.append((elapsed, cpu_usage))
        return cpu_data
    
    @staticmethod
    def parse_ram_log(ram_log_path):
        ram_data = []
        index = 0
        with open(ram_log_path, 'r') as f:
            for line in f:
                if line.startswith('Total:'):
                    parts = line.split()
                    total = float(parts[1])
                    used = float(parts[2])
                    ram_usage = (used / total) * 100
                    ram_data.append((index, ram_usage))
                    index += 1
        return ram_data

class TestCaseProcessor:
    def __init__(self):
        self.stats_cache = {}
        
    def process(self, test_case):
        key = test_case['lab_name']
        if key not in self.stats_cache:
            self.stats_cache[key] = self._calculate_stats(test_case)
        return self.stats_cache[key]
    
    def _calculate_stats(self, test_case):
        avg_duration = LogParser.parse_time_log(test_case['time_log'])
        test_duration = int(round(avg_duration))
        
        cpu_data = LogParser.parse_cpu_log(test_case['cpu_log'])
        ram_data = LogParser.parse_ram_log(test_case['ram_log'])
        
        cpu_stats = self._process_resource(cpu_data, test_duration)
        ram_stats = self._process_resource(ram_data, test_duration)
        
        return {
            'lab_number': test_case['lab_number'],
            'is_correct': test_case['is_correct'],
            'time_avg': avg_duration,
            'cpu_min': cpu_stats['min'],
            'cpu_max': cpu_stats['max'],
            'cpu_mean': cpu_stats['mean'],
            'cpu_delta': cpu_stats['delta'],
            'ram_min': ram_stats['min'],
            'ram_max': ram_stats['max'],
            'ram_mean': ram_stats['mean'],
            'ram_delta': ram_stats['delta']
        }
    
    def _process_resource(self, data, duration):
        if not data:
            return {'min': 0, 'max': 0, 'mean': 0, 'delta': 0}
        
        idle_before = data[:10]
        load = data[10:10+duration]
        idle_after = data[10+duration:10+duration+10]
        
        load_stats = self._calculate_basic_stats(load)
        idle_stats = self._calculate_basic_stats(idle_before + idle_after)
        
        return {
            'min': load_stats['min'],
            'max': load_stats['max'],
            'mean': load_stats['mean'],
            'delta': load_stats['mean'] - idle_stats['mean']
        }
    
    @staticmethod
    def _calculate_basic_stats(data):
        if not data:
            return {'min': 0, 'max': 0, 'mean': 0}
        values = [d[1] for d in data]
        return {
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values)
        }

class ReportGenerator:
    def __init__(self, df):
        self.df = df
    
    def generate_reports(self):
        return (
            self._generate_per_lab_report(),
            self._generate_overall_report()
        )
    
    def _generate_per_lab_report(self):
        report = []
        for lab_number in sorted(self.df['lab_number'].unique()):
            lab_data = self.df[self.df['lab_number'] == lab_number]
            report.extend(self._process_lab_data(lab_number, lab_data))
        return pd.DataFrame(report)
    
    def _process_lab_data(self, lab_number, lab_data):
        return [
            self._create_report_row(lab_number, lab_data[lab_data['is_correct']], 'correct'),
            self._create_report_row(lab_number, lab_data[~lab_data['is_correct']], 'incorrect')
        ]
    
    def _create_report_row(self, lab_number, data, test_type):
        if data.empty:
            return {
                'lab_number': lab_number,
                'type': test_type,
                **{col: 0 for col in self.df.columns if col not in ['lab_number', 'is_correct']}
            }
        return {
            'lab_number': lab_number,
            'type': test_type,
            'time_avg': data['time_avg'].mean(),
            'cpu_min': data['cpu_min'].mean(),
            'cpu_max': data['cpu_max'].mean(),
            'cpu_mean': data['cpu_mean'].mean(),
            'cpu_delta': data['cpu_delta'].mean(),
            'ram_min': data['ram_min'].mean(),
            'ram_max': data['ram_max'].mean(),
            'ram_mean': data['ram_mean'].mean(),
            'ram_delta': data['ram_delta'].mean()
        }
    
    def _generate_overall_report(self):
        return {
            'correct': self._calculate_group_stats(self.df[self.df['is_correct']]),
            'incorrect': self._calculate_group_stats(self.df[~self.df['is_correct']])
        }
    
    def _calculate_group_stats(self, group):
        return {
            'time_avg': group['time_avg'].mean(),
            'cpu_max_avg': group['cpu_max'].mean(),
            'cpu_min_avg': group['cpu_min'].mean(),
            'cpu_mean_avg': group['cpu_mean'].mean(),
            'cpu_delta_avg': group['cpu_delta'].mean(),
            'ram_max_avg': group['ram_max'].mean(),
            'ram_min_avg': group['ram_min'].mean(),
            'ram_mean_avg': group['ram_mean'].mean(),
            'ram_delta_avg': group['ram_delta'].mean()
        }

class TestReporter:
    @staticmethod
    def print_report(report_part1, report_part2):
        print("Часть 1: Аналитика по лабораториям\n")
        for _, row in report_part1.iterrows():
            print(f"Лабораторная {row['lab_number']}")
            print(f"{row['type'].capitalize()} тест")
            print(f"Время выполнения: {row['time_avg']:.2f} мс")
            print(f"CPU: Мин={row['cpu_min']:.2f}%, Макс={row['cpu_max']:.2f}%, Среднее={row['cpu_mean']:.2f}%, Дельта={row['cpu_delta']:.2f}%")
            print(f"RAM: Мин={row['ram_min']:.2f}%, Макс={row['ram_max']:.2f}%, Среднее={row['ram_mean']:.2f}%, Дельта={row['ram_delta']:.2f}%")
            print()
        
        print("\nЧасть 2: Сводная статистика\n")
        TestReporter._print_group_report('Корректные тесты', report_part2['correct'])
        TestReporter._print_group_report('Некорректные тесты', report_part2['incorrect'])
    
    @staticmethod
    def _print_group_report(title, data):
        print(f"{title}:")
        print(f"Среднее время: {data['time_avg']:.2f} мс")
        print(f"CPU: Средний макс={data['cpu_max_avg']:.2f}%, Средний мин={data['cpu_min_avg']:.2f}%")
        print(f"     Среднее={data['cpu_mean_avg']:.2f}%, Дельта={data['cpu_delta_avg']:.2f}%")
        print(f"RAM: Средний макс={data['ram_max_avg']:.2f}%, Средний мин={data['ram_min_avg']:.2f}%")
        print(f"     Среднее={data['ram_mean_avg']:.2f}%, Дельта={data['ram_delta_avg']:.2f}%")

class DataVisualizer:
    def __init__(self, df, per_lab_report, overall_report):
        self.df = df.copy()
        self.per_lab_report = per_lab_report
        self.overall_report = overall_report
        self.color_palette = {
            'correct': {
                'base': '#006400',
                'delta': '#90EE90'
            },
            'incorrect': {
                'base': '#8B0000',
                'delta': '#FF9999'
            }
        }
        sns.set_theme(style="whitegrid")
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.titleweight'] = 'bold'

    def generate_all_visualizations(self):
        try:
            self._plot_execution_time_comparison()
            self._plot_resource_analysis('cpu')
            self._plot_resource_analysis('ram')
            self._plot_combined_deltas()
        except Exception as e:
            print(f"Ошибка генерации: {str(e)}")

    def _plot_resource_analysis(self, resource):
        plt.figure(figsize=(16, 8))
        df = self.per_lab_report.copy()
        df['idle'] = df[f'{resource}_mean'] - df[f'{resource}_delta']
        
        labs = sorted(df['lab_number'].unique())
        bar_width = 0.35
        positions = np.arange(len(labs)) * 1.5
        
        fig, ax = plt.subplots()
        
        for i, test_type in enumerate(['correct', 'incorrect']):
            subset = df[df['type'] == test_type]
            colors = self.color_palette[test_type]
            
            ax.bar(
                positions + i*bar_width,
                subset['idle'],
                width=bar_width,
                color=colors['base'],
                edgecolor='black',
                linewidth=0.5,
                zorder=2,
                label='_'
            )
            
            ax.bar(
                positions + i*bar_width,
                subset[f'{resource}_delta'],
                bottom=subset['idle'],
                width=bar_width,
                color=colors['delta'],
                edgecolor='black',
                linewidth=0.5,
                zorder=2,
                label='_'
            )
    
        ax.set_xticks(positions + bar_width/2)
        ax.set_xticklabels(labs)
        ax.set_title(f"Анализ использования {resource.upper()}\nОтображение фонового потребления и под нагрзкой", pad=20)
        ax.set_xlabel("Номер лабораторной работы", labelpad=15)
        ax.set_ylabel(f"Использование {resource.upper()} (%)", labelpad=15)
        ax.grid(True, axis='y', zorder=1, linestyle='--', alpha=0.7)
        
        legend_elements = [
            plt.Rectangle((0,0),1,1, fc=self.color_palette['correct']['base'], ec='black', label='Корректные'),
            plt.Rectangle((0,0),1,1, fc=self.color_palette['correct']['delta'], ec='black', label='Дельта'),
            plt.Rectangle((0,0),1,1, fc=self.color_palette['incorrect']['base'], ec='black', label='Некорректные'),
            plt.Rectangle((0,0),1,1, fc=self.color_palette['incorrect']['delta'], ec='black', label='Дельта')
        ]

        ax.legend(title="Тип теста:", handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5))
 
        for pos in positions + bar_width*2:
            ax.axvline(pos - bar_width*1.5, color='gray', linestyle=':', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(f"{resource}_stacked_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_execution_time_comparison(self):
        plt.figure(figsize=(14, 7))
        ax = sns.barplot(
            x="lab_number",
            y="time_avg",
            hue="type",
            data=self.per_lab_report,
            palette={
                'correct': self.color_palette['correct']['base'],
                'incorrect': self.color_palette['incorrect']['base']
            },
            errorbar=None,
            edgecolor="black",
            linewidth=1
        )
        
        for container in ax.containers:
            ax.bar_label(
                container,
                fmt='%.1f ms',
                label_type='edge',
                padding=5,
                fontsize=9
            )
            
        ax.set_title("СРЕДНЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ", pad=20)
        ax.set_xlabel("Номер лабораторной работы", labelpad=15)
        ax.set_ylabel("Время (мс)", labelpad=15)
        ax.legend(title="Тип теста")
        plt.tight_layout()
        plt.savefig("execution_time_comparison.png", dpi=300)
        plt.close()

    # def _plot_combined_deltas(self):
    #     fig, axes = plt.subplots(1, 2, figsize=(18, 8))
        
    #     for idx, resource in enumerate(['cpu', 'ram']):
    #         sns.barplot(
    #             x="lab_number",
    #             y=f"{resource}_delta",
    #             hue="type",
    #             data=self.per_lab_report,
    #             palette={
    #                 'correct': self.color_palette['correct']['delta'],
    #                 'incorrect': self.color_palette['incorrect']['delta']
    #             },
    #             ax=axes[idx],
    #             edgecolor="black",
    #             linewidth=0.5
    #         )
            
    #         axes[idx].set_title(f"Различия {resource.upper()}", pad=15)
    #         axes[idx].set_xlabel("Номер работы", labelpad=10)
    #         axes[idx].set_ylabel(f"Δ {resource.upper()} (%)", labelpad=10)
            
    #         for container in axes[idx].containers:
    #             axes[idx].bar_label(
    #                 container,
    #                 fmt='Δ%.1f%%',
    #                 label_type='edge',
    #                 padding=2,
    #                 fontsize=9
    #             )
        
    #     plt.tight_layout()
    #     plt.savefig("combined_deltas.png", dpi=300)
    #     plt.close()

    def _plot_combined_deltas(self):
        fig, axes = plt.subplots(1, 2, figsize=(18, 8))
        
        for idx, resource in enumerate(['cpu', 'ram']):
            ax = axes[idx]

            sns.barplot(
                x="lab_number",
                y=f"{resource}_delta",
                hue="type",
                data=self.per_lab_report,
                palette={
                    'correct': self.color_palette['correct']['delta'],
                    'incorrect': self.color_palette['incorrect']['delta']
                },
                ax=ax,
                edgecolor="black",
                linewidth=0.5
            )

            # Убираем легенду с каждого графика
            legend = ax.get_legend()
            if legend is not None:
                legend.remove()
            
            ax.set_title(f"Различия {resource.upper()}", pad=15, fontsize=20)
            ax.set_xlabel("Номер работы", labelpad=10, fontsize=16)
            ax.set_ylabel(f"Δ {resource.upper()}, %", labelpad=10, fontsize=16)

            ax.tick_params(axis='both', labelsize=13)
            
            for container in ax.containers:
                ax.bar_label(
                    container,
                    fmt='Δ%.1f%%',
                    label_type='edge',
                    padding=5,
                    fontsize=18
                )
        
        plt.tight_layout()
        plt.savefig("combined_deltas.png", dpi=900, bbox_inches="tight")
        plt.close()



if __name__ == '__main__':
    collector = TestCaseCollector('.')
    test_cases = collector.collect()
    
    processor = TestCaseProcessor()
    processed = [processor.process(case) for case in test_cases]
    df = pd.DataFrame(processed)
    
    report_gen = ReportGenerator(df)
    report_part1, report_part2 = report_gen.generate_reports()
    
    TestReporter.print_report(report_part1, report_part2)
    
    visualizer = DataVisualizer(df, report_part1, report_part2)
    visualizer.generate_all_visualizations()