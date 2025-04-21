import numpy as np
import matplotlib.pyplot as plt
import random

class ExponentialGrowthSimulator:
    def __init__(self, base_probability=0.2, growth_rate=0.25):
        self.base_probability = base_probability
        self.growth_rate = growth_rate

    def calculate_probability(self, minute: int) -> float:
        # 計算 0 到 60 分鐘內的指數成長機率
        if minute < 0 or minute > 60:
            raise ValueError('Minute must be between 0 and 60.')
        probability = self.base_probability * np.exp(self.growth_rate * minute)
        return min(1, probability)

    def get_random_reply_time(self) -> int:
        """
        返回一個根據指數成長分佈隨機生成的 0 到 60 的整數。
        """
        for minute in range(61):
            if random.random() < self.calculate_probability(minute):
                if minute<1:
                    return 1
                return minute
        return 60  # 如果都沒有命中，返回 60


    def simulate_probability_growth(self):
        minutes = range(61)
        probabilities = [self.calculate_probability(m) for m in minutes]
        plt.plot(minutes, probabilities)
        plt.xlabel('Minutes (0 to 60)')
        plt.ylabel('Reply Probability')
        plt.title('Exponential Growth of Reply Probability')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

if __name__ == '__main__':
    simulator = ExponentialGrowthSimulator()
    simulator.simulate_probability_growth()
    reply_time = simulator.get_random_reply_time()
    print(f'Random reply time: {reply_time} minutes')

