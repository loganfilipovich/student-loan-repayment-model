from datetime import datetime
import matplotlib.pyplot as plt
import calendar


class RepaymentModel:
    """
    A class representing the repayment structure for a student loan.

    Attributes:
        upfront (float): The upfront payment amount.
        monthly (float): The monthly repayment amount.
    """
    def __init__(self, upfront: float = 0.0, monthly: float = 0.0):
        """
        Initialize the RepaymentModel object with upfront and monthly payments.

        Args:
            upfront (float): The upfront payment amount.
            monthly (float): The monthly repayment amount.
        """
        self.upfront = upfront
        self.monthly = monthly


class StudentLoanModel:
    """
    A class to simulate the repayment of a student loan over time.

    Attributes:
        current_date (datetime): The starting date of the loan.
        loan_value (float): The initial value of the loan.
        write_off_date (datetime): The date when the loan is written off.
        current_salary (float): The initial salary of the borrower.
        salary_increase (float): The annual salary increase (in percentage).
        repayment (RepaymentModel): The repayment structure (upfront and monthly payments).
        increase_type (str): The type of salary increase ('percent' or 'fixed').
        repayment_threshold (float): The salary threshold for loan repayments.
        repayment_rate (float): The repayment rate on income above the threshold.
        interest_rate (float): The annual interest rate on the loan.
    """
    
    def __init__(
        self,
        current_date: datetime,
        loan_value: float,
        write_off_date: datetime,
        current_salary: float,
        salary_increase: float,
        repayment: RepaymentModel = None,
        increase_type: str = 'percent',
        repayment_threshold: float = 27295,
        repayment_rate: float = 0.09,
        interest_rate: float = 0.043
    ):
        """
        Initialize the StudentLoanModel object with all required parameters.

        Args:
            current_date (datetime): The starting date of the loan.
            loan_value (float): The initial value of the loan.
            write_off_date (datetime): The date when the loan is written off.
            current_salary (float): The initial salary of the borrower.
            salary_increase (float): The annual salary increase (in percentage).
            repayment (RepaymentModel, optional): The repayment structure (upfront and monthly payments).
            increase_type (str): The type of salary increase ('percent' or 'fixed').
            repayment_threshold (float): The salary threshold for loan repayments.
            repayment_rate (float): The repayment rate on income above the threshold.
            interest_rate (float): The annual interest rate on the loan.
        """
        self.current_date = current_date
        self.loan_value = loan_value
        self.write_off_date = write_off_date
        self.initial_salary = current_salary
        self.salary_increase = salary_increase
        self.repayment = repayment if repayment else RepaymentModel()
        self.increase_type = increase_type
        self.repayment_threshold = repayment_threshold
        self.repayment_rate = repayment_rate
        self.interest_rate = interest_rate

        # Internal state variables
        self.loan_balance = loan_value
        self.total_repaid = 0.0
        self.net_salary_lost = 0.0  # Accumulated net salary lost
        self.repaid_in_full = False
        self.months_repaying = 0

        # Data for plotting
        self.dates = []
        self.salaries = []
        self.balances = []
        self.total_repayments = []
        self.net_salary_lost_history = []
        self.salary_after_tax_history = []  # Store salary after tax and NI

    def _apply_interest_monthly(self, balance: float) -> float:
        """
        Apply monthly interest on the current loan balance.

        Args:
            balance (float): The current loan balance.

        Returns:
            float: The updated loan balance after interest.
        """
        monthly_interest_rate = self.interest_rate / 12
        return balance * (1 + monthly_interest_rate)

    def _apply_salary_increase(self, salary: float) -> float:
        """
        Apply the annual salary increase based on the specified increase type.

        Args:
            salary (float): The current salary of the borrower.

        Returns:
            float: The updated salary after applying the increase.
        """
        if self.increase_type == 'percent':
            return salary * (1 + self.salary_increase / 100)
        else:
            return salary + self.salary_increase

    def _calculate_income_tax(self, salary: float) -> float:
        """
        Calculate the income tax based on UK 2023-24 tax brackets.

        Args:
            salary (float): The current salary of the borrower.

        Returns:
            float: The total income tax payable.
        """
        tax = 0
        brackets = [
            (12570, 0.0),        # Personal Allowance
            (50270, 0.20),       # Basic rate up to £50,270
            (125140, 0.40),      # Higher rate up to £125,140
            (float('inf'), 0.45) # Additional rate
        ]

        prev_limit = 0
        remaining_salary = salary

        for limit, rate in brackets:
            taxable_income = min(limit - prev_limit, remaining_salary)
            if taxable_income <= 0:
                break
            tax += taxable_income * rate
            remaining_salary -= taxable_income
            prev_limit = limit

        return tax

    def _calculate_national_insurance(self, salary: float) -> float:
        """
        Calculate the National Insurance (NI) contribution based on UK 2023-24 rates.

        Args:
            salary (float): The current salary of the borrower.

        Returns:
            float: The total National Insurance contribution.
        """
        ni_contrib = 0.0
        primary_threshold = 12570  # Below this, no NI contribution
        upper_earnings_limit = 50270  # Upper limit for 12% NI
        higher_rate = 0.02  # 2% on income above upper limit
        main_rate = 0.12  # 12% for earnings between £12,570 and £50,270

        if salary > primary_threshold:
            if salary <= upper_earnings_limit:
                ni_contrib = (salary - primary_threshold) * main_rate
            else:
                ni_contrib = (upper_earnings_limit - primary_threshold) * main_rate
                ni_contrib += (salary - upper_earnings_limit) * higher_rate

        return ni_contrib

    def _salary_repayment(self, salary: float) -> float:
        """
        Calculate the loan repayment based on the borrower's income.

        Args:
            salary (float): The current salary of the borrower.

        Returns:
            float: The amount of money to be repaid based on income.
        """
        repayable_income = max(0, salary - self.repayment_threshold)
        return repayable_income * self.repayment_rate

    def _get_next_month_date(self, current_date: datetime) -> datetime:
        """
        Get the date of the last day of the next month.

        Args:
            current_date (datetime): The current date.

        Returns:
            datetime: The last day of the next month.
        """
        year = current_date.year
        month = current_date.month
        next_month = month % 12 + 1
        next_year = year if next_month > month else year + 1
        last_day_next_month = calendar.monthrange(next_year, next_month)[1]
        return datetime(next_year, next_month, last_day_next_month)

    def simulate(self):
        """
        Simulate the student loan repayment over time, including salary increases, tax, NI, and repayments.

        The simulation continues until the loan is either repaid in full or written off.
        """
        self.loan_balance = self.loan_value
        self.total_repaid = 0.0
        self.net_salary_lost = 0.0
        self.months_repaying = 0
        self.repaid_in_full = False

        self.dates.clear()
        self.salaries.clear()
        self.balances.clear()
        self.total_repayments.clear()
        self.net_salary_lost_history.clear()
        self.salary_after_tax_history.clear()

        # Apply upfront repayment immediately
        upfront_payment = min(self.repayment.upfront, self.loan_balance)
        self.loan_balance -= upfront_payment
        self.total_repaid += upfront_payment

        current_date = self.current_date
        salary = self.initial_salary

        # Helper to track year for salary increase
        current_year = current_date.year

        while current_date < self.write_off_date and self.loan_balance > 0:
            self.dates.append(current_date)
            self.salaries.append(salary)
            self.balances.append(self.loan_balance)
            self.total_repayments.append(self.total_repaid)
            self.net_salary_lost_history.append(self.net_salary_lost)

            # Calculate salary after tax and NI
            income_tax_no_repayment = self._calculate_income_tax(salary)
            ni_contrib_no_repayment = self._calculate_national_insurance(salary)
            salary_after_tax_no_repayment = salary - income_tax_no_repayment - ni_contrib_no_repayment
            
            repayment_from_salary = self._salary_repayment(salary)
            salary_after_repayment = salary - repayment_from_salary
            income_tax_with_repayment = self._calculate_income_tax(salary_after_repayment)
            ni_contrib_with_repayment = self._calculate_national_insurance(salary_after_repayment)
            salary_after_tax_with_repayment = salary_after_repayment - income_tax_with_repayment - ni_contrib_with_repayment
            self.salary_after_tax_history.append(salary_after_tax_with_repayment)
            
            # Calculate the net salary loss
            net_salary_loss = salary_after_tax_no_repayment - salary_after_tax_with_repayment
            self.net_salary_lost += net_salary_loss / 12

            # Calculate repayments
            monthly_repayment_from_salary = self._salary_repayment(salary) / 12
            monthly_fixed_repayment = self.repayment.monthly
            total_monthly_repayment = monthly_repayment_from_salary + monthly_fixed_repayment
            actual_repayment = min(total_monthly_repayment, self.loan_balance)

            # Update loan balance and total repayments
            self.loan_balance -= actual_repayment
            self.total_repaid += actual_repayment

            # Apply monthly interest
            self.loan_balance = self._apply_interest_monthly(self.loan_balance)

            # Apply salary increase once per year
            if current_date.year > current_year:
                salary = self._apply_salary_increase(salary)
                current_year = current_date.year

            self.months_repaying += 1
            current_date = self._get_next_month_date(current_date)

            if self.loan_balance <= 0:
                self.loan_balance = 0.0
                self.repaid_in_full = True
                break

    def get_summary(self) -> dict:
        """
        Get a summary of the loan repayment including total repaid, net salary lost, and other details.

        Returns:
            dict: A dictionary containing the summary of the loan repayment.
        """
        months = self.months_repaying
        years = months // 12 + (1 if months % 12 else 0)

        total_repayments = self.repayment.upfront + self.repayment.monthly * months
        total_net_salary_lost_plus_repayments = self.net_salary_lost + total_repayments

        return {
            "Total repaid": round(self.total_repaid, 2),
            "Net salary lost (after tax + NI)": round(self.net_salary_lost, 2),
            "Remaining loan balance": round(self.loan_balance, 2),
            "Loan repaid in full": self.repaid_in_full,
            "Months repaying": months,
            "Years repaying (approx)": years,
            "Total net salary lost + repayments": round(total_net_salary_lost_plus_repayments, 2)
        }

    def print_summary(self):
        """
        Print the summary of the loan repayment to the console.
        """
        summary = self.get_summary()
        for key, value in summary.items():
            print(f"{key}: {value}")

    def plot_repayment_summary(self):
        """
        Plot the repayment summary, showing salary, loan balance, total repayments, 
        net salary lost, and salary after tax over time.
        """
        if not self.dates:
            print("No simulation data found. Please run simulate() first.")
            return

        plt.figure(figsize=(12, 6))
        plt.plot(self.dates, self.salaries, label="Salary", color='#657C6A', drawstyle='steps-pre')
        plt.plot(self.dates, self.balances, label="Loan Balance", color='#BB3E00', drawstyle='steps-pre')
        plt.plot(self.dates, self.total_repayments, label="Total Repaid", color='#F7AD45', drawstyle='steps-pre')
        plt.plot(self.dates, self.net_salary_lost_history, label="Net Salary Lost (After Tax + NI)", color='#F7AD45', linestyle='--', drawstyle='steps-pre')
        plt.plot(self.dates, self.salary_after_tax_history, label="Salary (After Tax + NI)", color='#657C6A', linestyle='--', drawstyle='steps-pre')

        plt.title("Student Loan Repayment Over Time")
        plt.xlabel("Date")
        plt.ylabel("Amount (£)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
