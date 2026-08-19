\# GSM8K Dataset



\## Dataset



Name:

GSM8K



Source:

OpenAI / Hugging Face



Dataset identifier:

openai/gsm8k



Configuration:

main



\## Splits



Train:

7473 samples



Test:

1319 samples



\## Fields



\- question

\- answer



\## Answer Structure



The `question` field contains the mathematical word problem.



The `answer` field contains a step-by-step reasoning trace followed by the final answer.



The final answer is normally marked using:



\#### <final\_answer>



Example:



A problem describes several arithmetic operations.



The reasoning trace performs the required calculations.



The answer ends with:



\#### 19



Therefore, the final numerical answer is 19.



\## Project Usage



Train split:



Used for Teacher-generated reasoning data and development experiments.



Test split:



Reserved for evaluation.



The GSM8K test split must not be used for Student training or Teacher-generated training data.



\## Current Status



Dataset loading: PASS



Train split: PASS



Test split: PASS



Required fields: PASS



Dataset inspection: PASS



GSM8K is ready for Teacher generation experiments.

