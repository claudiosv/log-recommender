#!/usr/bin/env bash

# Tunable params
UPLOAD_TO_GOOGLE=0
MIN_WORD_OCCURENCIES=1500
MIN_WORD_FREQUNCY=0.0002
MIN_FOUND_IN_PROJECTS_FREQUENCY=0.5
MIN_LOG_NUMBER_PER_PROJECT=100
WORD_TO_VEC_N_VECTOR_DIMENSIONS=150
MAX_ITER_RAE=3
MAX_SENTENCE_LENGTH_RAE=50

# Non tunable params
GENERATED_STATS_FOLDER="generated_stats"
OUTPUT_CORPUS_FILE='../gengram/corpus.txt'
PREPROCESSED_LOG_FILE='pplogs.pkl'
PROJECT_STATS_FILE="${GENERATED_STATS_FOLDER}/project_stats.csv"
OUTPUT_FREQUENCIES_FILE="${GENERATED_STATS_FOLDER}/frequencies.csv"
OUTPUT_FIRST_WORD_FREQUENCIES_FILE="${GENERATED_STATS_FOLDER}/frequencies_first_word.csv"
OUTPUT_DISTRIBUTION_BY_LEVELS_FILE="${GENERATED_STATS_FOLDER}/level_distribution.csv"
OUTPUT_DISTRIBUTION_BY_N_VARS_FILE="${GENERATED_STATS_FOLDER}/n_vars_distribution.csv"
PATH_TO_PYTHON='/home/hlib/dev/bz-hackathon/env/bin/python'
PATH_TO_CACHED_PROJECTS='../.Projects'
SPREADSHEET_OUTPUT_DIR_NAME='logs'
AUTOENCODE_LOCATION='../AutoenCODE'
OUTPUT_CONTEXT_CORPUS_FILE="${AUTOENCODE_LOCATION}/data/corpus.src"

POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -e|--extract-logs)
    PROJECT_LIST_FILE="$2"
    shift 2
    ;;
    -u|--upload-to-google)
    UPLOAD_TO_GOOGLE=1
    shift
    ;;
    *)    # unknown option
    POSITIONAL+=("$1") # save it in an array for later
    shift # past argument
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

if ! [ -d $GENERATED_STATS_FOLDER ]; then
    mkdir $GENERATED_STATS_FOLDER
fi

if [ -n "$PROJECT_LIST_FILE" ]; then
    mv ../.Logs .
    SCRIPT="$(pwd)/log-extractor.sh ${PROJECT_LIST_FILE}"
    if [ -n "$PATH_TO_CACHED_PROJECTS" ]; then
        SCRIPT="$SCRIPT $PATH_TO_CACHED_PROJECTS"
    fi
    echo "Extracting logs: running $SCRIPT"
    eval "$SCRIPT"
    mv .Logs/ ..
else
    echo "Not extracting logs, working with existing ones"
fi

LOG_PREPROCESSOR_SCRIPT="$PATH_TO_PYTHON log_preprocessor.py"
LOG_PREPROCESSOR_SCRIPT="$LOG_PREPROCESSOR_SCRIPT --min-log-number-per-project $MIN_LOG_NUMBER_PER_PROJECT"
LOG_PREPROCESSOR_SCRIPT="$LOG_PREPROCESSOR_SCRIPT --output-corpus-file $OUTPUT_CORPUS_FILE"
LOG_PREPROCESSOR_SCRIPT="$LOG_PREPROCESSOR_SCRIPT --output-context-corpus-file $OUTPUT_CONTEXT_CORPUS_FILE"
LOG_PREPROCESSOR_SCRIPT="$LOG_PREPROCESSOR_SCRIPT --output-preprocessed-log-file $PREPROCESSED_LOG_FILE"
LOG_PREPROCESSOR_SCRIPT="$LOG_PREPROCESSOR_SCRIPT --output-project-stats-file $PROJECT_STATS_FILE"

echo "Running $LOG_PREPROCESSOR_SCRIPT"
eval "$LOG_PREPROCESSOR_SCRIPT"
ERR_CODE=$?
if [ $ERR_CODE -ne 0 ]; then
    exit 1
fi

if ! [ -d "$SPREADSHEET_OUTPUT_DIR_NAME" ]; then
    mkdir "$SPREADSHEET_OUTPUT_DIR_NAME"
fi
FREQ_SCRIPT="$PATH_TO_PYTHON /home/hlib/thesis/log-recommender/freqs.py"
FREQ_SCRIPT="$FREQ_SCRIPT --min-log-number-per-project $MIN_LOG_NUMBER_PER_PROJECT"
FREQ_SCRIPT="$FREQ_SCRIPT --min-word-occurencies $MIN_WORD_OCCURENCIES"
FREQ_SCRIPT="$FREQ_SCRIPT --min-word-frequency $MIN_WORD_FREQUNCY"
FREQ_SCRIPT="$FREQ_SCRIPT --min-found-in-projects-frequency $MIN_FOUND_IN_PROJECTS_FREQUENCY"

FREQ_SCRIPT="$FREQ_SCRIPT --input-preprocessed-log-file $PREPROCESSED_LOG_FILE"
FREQ_SCRIPT="$FREQ_SCRIPT --input-project-stats-file $PROJECT_STATS_FILE"
FREQ_SCRIPT="$FREQ_SCRIPT --output-frequencies-file $OUTPUT_FREQUENCIES_FILE"
FREQ_SCRIPT="$FREQ_SCRIPT --output-first-word-frequencies-file $OUTPUT_FIRST_WORD_FREQUENCIES_FILE"
FREQ_SCRIPT="$FREQ_SCRIPT --output-distribution-by-levels-file $OUTPUT_DISTRIBUTION_BY_LEVELS_FILE"
FREQ_SCRIPT="$FREQ_SCRIPT --output-distribution-by-n_vars-file $OUTPUT_DISTRIBUTION_BY_N_VARS_FILE"
FREQ_SCRIPT="$FREQ_SCRIPT --spreadsheet-output-dir-name $SPREADSHEET_OUTPUT_DIR_NAME"

if [ "$UPLOAD_TO_GOOGLE" -eq "1" ]; then
    echo "Uploading csvs to google..."
    UPLOAD_TO_GOOGLE_SCRIPT="$PATH_TO_PYTHON upload_to_google.py $SPREADSHEET_OUTPUT_DIR_NAME"
    eval "$UPLOAD_TO_GOOGLE_SCRIPT"
    ERR_CODE=$?
    if [ $ERR_CODE -ne 0 ]; then
        exit 1
    fi
fi

echo "Running $FREQ_SCRIPT"
eval "$FREQ_SCRIPT"
ERR_CODE=$?
if [ $ERR_CODE -ne 0 ]; then
    exit 1
fi

FIRST_WORD_PICKER_SCRIPT="$PATH_TO_PYTHON first_word_picker.py --input-preprocessed-log-file $PREPROCESSED_LOG_FILE"
FIRST_WORD_PICKER_SCRIPT="$FIRST_WORD_PICKER_SCRIPT --min-word-occurencies $MIN_WORD_OCCURENCIES"
echo "Running $FIRST_WORD_PICKER_SCRIPT"
eval "$FIRST_WORD_PICKER_SCRIPT"
ERR_CODE=$?
if [ $ERR_CODE -ne 0 ]; then
    exit 1
fi

cd "${AUTOENCODE_LOCATION}/bin"
CMD="./run_word2vec.sh ../data ../out/word2vec/ $WORD_TO_VEC_N_VECTOR_DIMENSIONS"
echo "Running $CMD"
eval "$CMD"
ERR_CODE=$?
if [ $ERR_CODE -ne 0 ]; then
    exit 1
fi

CMD="./run_postprocess.py --w2v ../out/word2vec/word2vec.out --src ../data"
echo "Running $CMD"
eval "$CMD"
ERR_CODE=$?
if [ $ERR_CODE -ne 0 ]; then
    exit 1
fi

CMD="rae/run_rae.sh ../out ../out $MAX_SENTENCE_LENGTH_RAE $MAX_ITER_RAE"
echo "Running $CMD"
eval "$CMD"
ERR_CODE=$?
if [ $ERR_CODE -ne 0 ]; then
    exit 1
fi