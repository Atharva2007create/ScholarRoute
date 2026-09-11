import type { ReferenceItem } from "./api/types";

const items = (kind: string, values: ReadonlyArray<readonly [string, string]>): ReferenceItem[] =>
  values.map(([code, name]) => ({ id: `${kind}-${code}`, code, name }));

export const engineeringBranches = items("engineering-branch", [
  ["CSE", "Computer Science and Engineering"],
  ["COMPUTER_ENGINEERING", "Computer Engineering"],
  ["IT", "Information Technology"],
  ["AI", "Artificial Intelligence"],
  ["AI_ML", "Artificial Intelligence and Machine Learning"],
  ["AI_DS", "Artificial Intelligence and Data Science"],
  ["DATA_SCIENCE", "Data Science"],
  ["MACHINE_LEARNING", "Machine Learning"],
  ["CYBER_SECURITY", "Cyber Security"],
  ["IOT", "Internet of Things"],
  ["SOFTWARE_ENGINEERING", "Software Engineering"],
  ["ECE", "Electronics and Communication Engineering"],
  ["ELECTRONICS_ENGINEERING", "Electronics Engineering"],
  ["ELECTRONICS_TELECOMMUNICATION", "Electronics and Telecommunication Engineering"],
  ["EE", "Electrical Engineering"],
  ["EEE", "Electrical and Electronics Engineering"],
  ["INSTRUMENTATION", "Instrumentation Engineering"],
  ["INSTRUMENTATION_CONTROL", "Instrumentation and Control Engineering"],
  ["ME", "Mechanical Engineering"],
  ["MECHATRONICS", "Mechatronics Engineering"],
  ["ROBOTICS_AUTOMATION", "Robotics and Automation"],
  ["AUTOMOBILE", "Automobile Engineering"],
  ["AUTOMOTIVE", "Automotive Engineering"],
  ["MANUFACTURING", "Manufacturing Engineering"],
  ["PRODUCTION", "Production Engineering"],
  ["INDUSTRIAL", "Industrial Engineering"],
  ["CIVIL", "Civil Engineering"],
  ["CONSTRUCTION", "Construction Engineering"],
  ["STRUCTURAL", "Structural Engineering"],
  ["ENVIRONMENTAL", "Environmental Engineering"],
  ["CHEMICAL", "Chemical Engineering"],
  ["PETROCHEMICAL", "Petrochemical Engineering"],
  ["PETROLEUM", "Petroleum Engineering"],
  ["POLYMER", "Polymer Engineering"],
  ["PLASTICS", "Plastics Engineering"],
  ["BIOTECHNOLOGY", "Biotechnology"],
  ["BIOMEDICAL", "Biomedical Engineering"],
  ["BIOENGINEERING", "Bioengineering"],
  ["BIOCHEMICAL", "Biochemical Engineering"],
  ["FOOD_TECHNOLOGY", "Food Technology"],
  ["FOOD_ENGINEERING", "Food Engineering"],
  ["AGRICULTURAL", "Agricultural Engineering"],
  ["AEROSPACE", "Aerospace Engineering"],
  ["AERONAUTICAL", "Aeronautical Engineering"],
  ["MARINE", "Marine Engineering"],
  ["NAVAL_ARCHITECTURE", "Naval Architecture"],
  ["MINING", "Mining Engineering"],
  ["METALLURGICAL", "Metallurgical Engineering"],
  ["MATERIALS", "Materials Engineering"],
  ["CERAMIC", "Ceramic Engineering"],
  ["TEXTILE", "Textile Engineering"],
  ["PRINTING", "Printing Engineering"],
  ["ENERGY", "Energy Engineering"],
  ["RENEWABLE_ENERGY", "Renewable Energy Engineering"],
  ["NUCLEAR", "Nuclear Engineering"],
  ["ENGINEERING_PHYSICS", "Engineering Physics"],
  ["MATHEMATICS_COMPUTING", "Mathematics and Computing"],
  ["COMPUTATIONAL_ENGINEERING", "Computational Engineering"],
  ["INDUSTRIAL_PRODUCTION", "Industrial and Production Engineering"],
]);

export const genderOptions = items("student-gender", [
  ["MALE", "Male"],
  ["FEMALE", "Female"],
  ["NON_BINARY", "Non-binary"],
  ["PREFER_NOT_TO_SAY", "Rather not say"],
]);

export function courseCodeForExam(examCode: string): string {
  if (examCode === "JEE_MAIN") return "BTECH";
  if (examCode === "NEET_UG") return "MBBS";
  return "";
}

export function branchOptionsForExam(examCode: string): ReferenceItem[] {
  return examCode === "JEE_MAIN" ? engineeringBranches : [];
}

export function genderPoolCodeForGender(genderCode: string): string | undefined {
  if (!genderCode) return undefined;
  return genderCode === "FEMALE" ? "FEMALE_ONLY" : "GENDER_NEUTRAL";
}
