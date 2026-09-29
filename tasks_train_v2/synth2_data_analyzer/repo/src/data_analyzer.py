class DataAnalyzer:
    def __init__(self, data):
        self.data = data

    def _calculate_average(self):
        return sum(self.data) / len(self.data)

    def get_average(self):
        average = self._calculate_average()
        return f'The average is {average}'
